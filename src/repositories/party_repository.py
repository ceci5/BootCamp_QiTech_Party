from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from database import Context
from models import Party, PartyStatus, PartyStatusEvent

# A UNIQUE(document_number) da tabela party, com o nome que o Postgres
# lhe dá (<tabela>_<coluna>_key; conferido com \d party).
DOCUMENT_NUMBER_CONSTRAINT = "party_document_number_key"


class PartyRepository:
    """A camada que fala com o banco pela parte. Só aqui existe query.

    Mesmo desenho do SampleEntityRepository: recebe o CONTEXTO do
    trabalho e tira dele a sessão. Nenhuma regra mora aqui — quem decide o
    que fazer com o que volta é o PartyController.
    """

    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_by_key(self, party_key: str) -> Party:
        """A parte desta chave, ou None.

        A coluna é CHAR(36), e no Postgres o CHAR ignora espaços no fim ao
        comparar: "<chave> " acharia a parte. A busca segue pelo índice, e
        a conferência exata é aqui, em Python (revisão de 2026-10-11).
        """
        party = self.session.query(Party).filter(Party.party_key == party_key).first()

        if party is not None and party.party_key != party_key:
            return None

        return party

    def get_by_document_number(self, document_number: str) -> Party:
        """A parte deste documento, ou None. A UNIQUE garante no máximo uma."""
        return self.session.query(Party).filter(Party.document_number == document_number).first()

    def get_status(self, enumerator: str) -> PartyStatus:
        return self.session.query(PartyStatus).filter(PartyStatus.enumerator == enumerator).one()

    def create_pending(self, party_data: dict, trace_id: str) -> Optional[Party]:
        """A parte nasce em pending, com o evento de nascimento junto.

        O evento não tem estado de origem (`from_status` nulo), leva o
        `actor` de quem pediu e nenhum `reason` (sumário C5).

        Devolve None se o documento já existe. Ninguém pergunta antes: o
        INSERT tenta, e a UNIQUE do banco responde — é a única resposta que
        vale também para duas requisições ao mesmo tempo, porque a segunda
        espera no índice até a primeira terminar. O SAVEPOINT existe para
        que a recusa desfaça só este INSERT, e não a transação inteira.
        Outra constraint que falhe não é "documento repetido": sobe.
        """
        party = Party()
        party.party_key = str(uuid4())
        party.name = party_data["name"]
        party.document_number = party_data["document_number"]
        party.pix_key = party_data.get("pix_key")
        party.status = self.get_status(PartyStatus.PENDING)

        birth_event = PartyStatusEvent()
        birth_event.from_status = None
        birth_event.to_status = party.status
        birth_event.actor = party_data["actor"]
        birth_event.reason = None
        birth_event.trace_id = trace_id
        birth_event.event_datetime = datetime.now(timezone.utc)

        party.status_events.append(birth_event)

        try:
            with self.session.begin_nested():
                self.session.add(party)
                self.session.flush()
        except IntegrityError as error:
            if error.orig.diag.constraint_name == DOCUMENT_NUMBER_CONSTRAINT:
                return None
            raise

        return party

    def get_by_key_for_update(self, party_key: str) -> Party:
        """A parte, travada até o fim da transação (SELECT ... FOR UPDATE OF party).

        Só a linha da parte trava, não a de party_status: partes
        diferentes não se esperam. O populate_existing relê do banco
        mesmo que o objeto já esteja na sessão — depois de um commit, o que
        está na memória pode ter ficado para trás.
        """
        return (
            self.session.query(Party)
            .filter(Party.party_key == party_key)
            .with_for_update(of=Party)
            .populate_existing()
            .first()
        )

    def update_status(
        self, party: Party, new_status_enumerator: str, actor: str, reason: str, trace_id: str
    ) -> None:
        """Muda o estado e grava o evento da transição, juntos (06 §1)."""
        new_status = self.get_status(new_status_enumerator)

        status_event = PartyStatusEvent()
        status_event.from_status = party.status
        status_event.to_status = new_status
        status_event.actor = actor
        status_event.reason = reason
        status_event.trace_id = trace_id
        status_event.event_datetime = datetime.now(timezone.utc)

        party.status = new_status
        party.status_events.append(status_event)
