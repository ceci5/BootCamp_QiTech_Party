from controllers.base_controller import BaseController
from dtos import ClientDTO
from errors import ClientMustBeOrganization, ClientNotFound, PartyAlreadyClient, PartyNotActive, PartyNotFound
from models import PartyStatus
from repositories import ClientRepository, PartyRepository
from utils.document_number import CNPJ_LENGTH


class ClientController(BaseController):
    """As regras de negócio do cliente: quem pode virar cliente da plataforma."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)
        self.party_repository = PartyRepository(self.context)

    def create(self, client_data: dict) -> dict:
        """Confere a parte e a torna cliente, com o preço da plataforma para ela.

        As perguntas vêm numa ordem de propósito (sumário L13): a parte
        existe? é jurídica? está ativa? Ser pessoa física é defeito
        permanente, e o estado pode mudar — por isso uma PF recusada pelo
        bureau ouve "não é jurídica", e não "não está ativa".

        A parte é lida sem trava. Ativa ela não deixa de ser (06 §2.1), e a
        única mudança possível no meio do caminho é pending → active: quem
        leu pending responde 409 com o que era verdade naquele instante, e
        repetir dá 201.

        Uma transação só, e nenhum outro serviço chamado: o commit fica na
        última linha, como na base.
        """
        party_key = client_data["party_key"]
        self.logger.debug(f"Tornando cliente a parte de chave {party_key}")

        party = self.party_repository.get_by_key(party_key)

        if party is None:
            raise PartyNotFound(party_key)

        # Jurídica é quem tem CNPJ: o documento só é usado pelo tamanho, e
        # não sai daqui para lugar nenhum (D0008).
        if len(party.document_number) != CNPJ_LENGTH:
            raise ClientMustBeOrganization(party_key)

        if party.status.enumerator != PartyStatus.ACTIVE:
            raise PartyNotActive(party_key, party.status.enumerator)

        client = self.client_repository.create(party, client_data)

        if client is None:
            raise PartyAlreadyClient(party_key)

        client_dto = ClientDTO.obj_to_dict(client)

        # O cliente não tem trilha de estado (06 §3): quem pediu fica no log,
        # ligado a esta requisição pelo identificador da linha (spec 04, P2;
        # como o sumário C5 faz com a repescagem). Só chaves e o actor.
        self.logger.info(
            f"Cliente {client_dto['client_key']} criado para a parte {party_key} "
            f"por {client_data['actor']}"
        )

        self.session.commit()

        return client_dto

    def get_by_key(self, client_key: str) -> dict:
        self.logger.debug(f"Buscando o cliente de chave {client_key}")

        client = self.client_repository.get_by_key(client_key)

        if client is None:
            raise ClientNotFound(client_key)

        return ClientDTO.obj_to_dict(client)
