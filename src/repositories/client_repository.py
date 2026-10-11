from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from database import Context
from models import Client, Party

# A UNIQUE(party_id) da tabela client, com o nome que o Postgres lhe dá
# (<tabela>_<coluna>_key; medido, spec 04).
PARTY_ID_CONSTRAINT = "client_party_id_key"


class ClientRepository:
    """A camada que fala com o banco pelo cliente. Só aqui existe query.

    Mesmo desenho do PartyRepository: recebe o CONTEXTO do trabalho e tira
    dele a sessão. Nenhuma regra mora aqui — quem decide quem pode virar
    cliente é o ClientController.
    """

    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_by_key(self, client_key: str) -> Client:
        return self.session.query(Client).filter(Client.client_key == client_key).first()

    def create(self, party: Party, client_data: dict) -> Optional[Client]:
        """O cliente, ligado à parte, com o preço que a plataforma cobra dela.

        O percentual chega como texto, no formato que o schema já cobrou, e
        vira Decimal aqui — nunca float (regras do repositório, "Dinheiro").

        Devolve None se a parte já é cliente. Ninguém pergunta antes: o
        INSERT tenta, e a UNIQUE(party_id) responde — também para dois
        pedidos ao mesmo tempo, porque o segundo espera no índice até o
        primeiro terminar. O SAVEPOINT desfaz só este INSERT. Outra
        constraint que falhe não é "já é cliente": sobe.
        """
        client = Client()
        client.client_key = str(uuid4())
        # Pela coluna, não pela relação: `client.party = party` também
        # faria `party.client = client`, e o ORM desligaria (party_id NULL)
        # o cliente que a parte já tivesse, em vez de deixar a UNIQUE
        # recusar o novo (spec 04, registro da T5).
        client.party_id = party.id
        client.platform_fee_percentage = Decimal(client_data["platform_fee_percentage"])

        try:
            with self.session.begin_nested():
                self.session.add(client)
                self.session.flush()
        except IntegrityError as error:
            if error.orig.diag.constraint_name == PARTY_ID_CONSTRAINT:
                return None
            raise

        return client
