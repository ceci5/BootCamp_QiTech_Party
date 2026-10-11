from connectors import BureauConnector
from controllers.base_controller import BaseController
from dtos import PartyDTO
from errors import DuplicatedPartyDocument, InvalidPartyDocument, PartyNotFound
from models import PartyStatus
from repositories import PartyRepository
from utils.document_number import CPF_LENGTH, is_valid_cnpj, is_valid_cpf
from utils.request_context import get_request_id

# Quem assina a transição que vem da resposta do bureau (06 §1, sumário C5).
BUREAU_ACTOR = "bureau"

# O que cada resposta do bureau faz com a parte.
STATUS_BY_BUREAU_RESULT = {
    BureauConnector.APPROVED: PartyStatus.ACTIVE,
    BureauConnector.REJECTED: PartyStatus.REJECTED,
}


class PartyController(BaseController):
    """As regras de negócio da parte: quem pode existir, e em que estado."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.party_repository = PartyRepository(self.context)
        self.bureau_connector = BureauConnector()

    def create(self, party_data: dict) -> dict:
        """Confere o documento, registra a parte em pending e pergunta ao bureau.

        O formato o schema já cobrou. Aqui é a conta dos dígitos
        verificadores, ANTES de qualquer escrita: uma recusa não deixa
        linha nenhuma no banco.

        ────────────────────────────────────────────────────────────────
        DOIS COMMITS NUMA REQUISIÇÃO — e o porquê (sumário C2; guia §14)
        ────────────────────────────────────────────────────────────────
        A regra da base é um commit, na última linha. Aqui são dois, cada
        um no fim de um método privado, porque o bureau é outro serviço e
        nunca se chama outro serviço com transação de banco aberta (01b
        §0.5; D0010): a parte é salva em pending, a transação fecha, o
        bureau é chamado sem nada aberto, e só então uma segunda transação
        grava o desfecho. Se o bureau não responder, não há segunda
        transação: a parte fica pending, e a repescagem resolve depois.

        Repare no que atravessa a chamada: só o dicionário de resposta e o
        documento que veio no pedido, nunca o objeto do banco. Depois do
        commit a sessão expira o objeto (expire_on_commit), e ler um
        atributo dele abriria uma transação nova — que ficaria aberta
        durante a espera inteira.
        """
        self.logger.debug("Cadastrando uma nova parte")

        document_number = party_data["document_number"]

        if not self._is_valid_document(document_number):
            raise InvalidPartyDocument()

        party_dto = self._register_pending(party_data)

        bureau_result = self.bureau_connector.verify(document_number)

        if bureau_result is not None:
            party_dto = self._apply_bureau_result(party_dto["party_key"], bureau_result)

        self.logger.info(f"Parte {party_dto['party_key']} cadastrada em {party_dto['status']}")

        return party_dto

    def get_by_key(self, party_key: str) -> dict:
        self.logger.debug(f"Buscando a parte de chave {party_key}")

        party = self.party_repository.get_by_key(party_key)

        if party is None:
            raise PartyNotFound(party_key)

        return PartyDTO.obj_to_dict(party)

    def _register_pending(self, party_data: dict) -> dict:
        """A primeira transação: a parte e o evento de nascimento, e o commit."""
        party = self.party_repository.create_pending(party_data, get_request_id())

        if party is None:
            raise DuplicatedPartyDocument()

        party_dto = PartyDTO.obj_to_creation_dict(party)
        self.session.commit()

        return party_dto

    def _apply_bureau_result(self, party_key: str, bureau_result: str) -> dict:
        """A segunda transação: o desfecho do bureau, se a parte ainda espera por ele.

        A parte é relida com trava. Se outra requisição já a tirou de
        pending (a repescagem da fatia 06, por exemplo), nada é gravado e
        sai o estado atual: quem decidiu primeiro vale (sumário L14). O
        commit acontece nos dois casos, para soltar a trava.
        """
        party = self.party_repository.get_by_key_for_update(party_key)

        if party.status.enumerator == PartyStatus.PENDING:
            self.party_repository.update_status(
                party,
                STATUS_BY_BUREAU_RESULT[bureau_result],
                actor=BUREAU_ACTOR,
                reason=bureau_result,
                trace_id=get_request_id(),
            )

        party_dto = PartyDTO.obj_to_creation_dict(party)
        self.session.commit()

        return party_dto

    def _is_valid_document(self, document_number: str) -> bool:
        if len(document_number) == CPF_LENGTH:
            return is_valid_cpf(document_number)

        return is_valid_cnpj(document_number)
