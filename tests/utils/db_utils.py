from os import environ
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import DBAPIError


RESET_QUERIES = [
    "DROP SCHEMA public CASCADE;",
    "CREATE SCHEMA public;",
    "GRANT ALL ON SCHEMA public TO CURRENT_USER;",
    "GRANT ALL ON SCHEMA public TO public;",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = PROJECT_ROOT / "database" / "database.sql"

DEFAULT_DATABASE_URL = "postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp"

DATABASE_OFFLINE = (
    "Não consegui falar com o banco em {host}:{port}.\n"
    "Ele precisa estar de pé pros testes rodarem. Suba com:  docker compose up\n"
    "Se ele já está de pé, confira a porta na DATABASE_URL do seu .env."
)


class DbUtils:
    """Apaga o banco inteiro e o recria do zero — quando alguém chama.

    Não existe limpeza automática neste projeto. O `rollback()` roda no
    teste que o chamar, na linha em que for chamado, e em mais lugar
    nenhum. Todos os testes dividem o mesmo banco, e cada um enxerga o
    que os anteriores deixaram pra trás.

    O nome engana um pouco: isto não desfaz uma transação. Ele derruba
    o schema `public` com tudo que estiver dentro e roda o
    `database/database.sql` de novo — tabelas vazias e os quatro status
    do INSERT de volta.

    Quando o seu teste precisa chamar: sempre que alguma asserção
    depender de QUANTAS linhas existem no banco — contar, listar,
    paginar, filtrar. Nesses casos `DbUtils.rollback()` é a primeira
    linha do teste, antes de criar qualquer coisa (o exemplo está em
    `tests/integration/test_sample_entities.py`). Um teste que só olha
    as entidades que ele mesmo criou, pela chave que recebeu de volta,
    não precisa de limpeza nenhuma — e fica mais rápido sem ela.

    A limpeza acontece pela mesma conexão que a aplicação usa (a
    DATABASE_URL), e não por um programa externo: quem tem Docker
    rodando já tem tudo que precisa.
    """

    @staticmethod
    def database_url() -> str:
        return environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

    @staticmethod
    def rollback() -> None:
        engine = create_engine(DbUtils.database_url(), isolation_level="AUTOCOMMIT")

        try:
            with engine.connect() as connection:
                for query in RESET_QUERIES:
                    connection.exec_driver_sql(query)

                connection.exec_driver_sql(SCHEMA_FILE.read_text())
        except OperationalError:
            message = DATABASE_OFFLINE.format(host=engine.url.host, port=engine.url.port)
            raise RuntimeError(message) from None
        finally:
            engine.dispose()

    # ────────────────────────────────────────────────────────────────
    # Leituras da party-api (spec 03 §8; sumário C8; guia §14)
    # ────────────────────────────────────────────────────────────────
    # Exceção declarada à regra "o teste só fala com o banco para zerar":
    # o trace_id dos eventos, o gatilho append-only e "nenhuma linha
    # gravada" não aparecem em resposta HTTP nenhuma, e o GET /parties/{key}
    # não pode ganhar campo (é consumido pelos outros dois serviços).
    # Nenhum destes métodos monta cenário: o cenário nasce por POST.

    @staticmethod
    def _execute(statement: str, parameters: dict = None) -> list:
        engine = create_engine(DbUtils.database_url())

        try:
            with engine.connect() as connection:
                rows = connection.execute(text(statement), parameters or {}).mappings().all()
                return [dict(row) for row in rows]
        finally:
            engine.dispose()

    @staticmethod
    def party_status_events(party_key: str) -> list:
        """A trilha de estado de uma parte, na ordem em que foi gravada."""
        return DbUtils._execute(
            """
            SELECT from_status.enumerator AS from_status,
                   to_status.enumerator AS to_status,
                   event.actor,
                   event.reason,
                   event.trace_id
              FROM party_status_event event
              JOIN party ON party.id = event.party_id
              LEFT JOIN party_status from_status ON from_status.id = event.from_status_id
              JOIN party_status to_status ON to_status.id = event.to_status_id
             WHERE party.party_key = :party_key
             ORDER BY event.id
            """,
            {"party_key": party_key},
        )

    # O que cada operação tenta fazer com a trilha de uma parte. O TRUNCATE
    # não tem WHERE: ele é a prova do gatilho de COMANDO, que o de linha não
    # pega.
    CHANGE_PARTY_STATUS_EVENTS = {
        "UPDATE": "UPDATE party_status_event SET actor = actor "
        "WHERE party_id = (SELECT id FROM party WHERE party_key = :party_key)",
        "DELETE": "DELETE FROM party_status_event "
        "WHERE party_id = (SELECT id FROM party WHERE party_key = :party_key)",
        "TRUNCATE": "TRUNCATE party_status_event",
    }

    @staticmethod
    def try_to_change_party_status_events(operation: str, party_key: str):
        """Tenta UPDATE, DELETE ou TRUNCATE na trilha e devolve o erro do banco.

        Devolve a mensagem do banco, ou None se o comando passou. A
        transação é SEMPRE desfeita: mesmo sem o gatilho (no vermelho), nada
        se perde.
        """
        statement = DbUtils.CHANGE_PARTY_STATUS_EVENTS[operation]
        engine = create_engine(DbUtils.database_url())

        try:
            with engine.connect() as connection:
                try:
                    connection.execute(text(statement), {"party_key": party_key})
                except DBAPIError as error:
                    return error.orig.diag.message_primary
                finally:
                    connection.rollback()
        finally:
            engine.dispose()

        return None

    @staticmethod
    def count_parties_by_document(document_number: str) -> int:
        """Quantas partes têm este documento: 0 depois de uma recusa, 1 sempre."""
        rows = DbUtils._execute(
            "SELECT count(*) AS total FROM party WHERE document_number = :document_number",
            {"document_number": document_number},
        )
        return rows[0]["total"]

    @staticmethod
    def count_idle_in_transaction() -> int:
        """Conexões deste banco paradas no meio de uma transação há mais de 300 ms.

        É a prova de que a API não segura transação aberta enquanto espera o
        bureau (01b §0.5): a 1ª e a 2ª transações do POST /parties duram
        milissegundos; uma transação esquecida aberta durante a chamada dura
        o tempo do bureau inteiro.
        """
        rows = DbUtils._execute(
            "SELECT count(*) AS total FROM pg_stat_activity "
            "WHERE datname = current_database() "
            "AND state = 'idle in transaction' "
            "AND now() - state_change > interval '300 milliseconds'"
        )
        return rows[0]["total"]
