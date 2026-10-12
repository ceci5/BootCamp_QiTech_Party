import re

import pytest

from tests.utils import ObjectGenerator, PayloadGenerator, RandomGenerator, RequestGenerator


# Os campos de GET /clients/{key} (01b §2). O POST /clients devolve o mesmo
# corpo (sumário L12). O Contrato lê esta rota: campo a mais ou a menos
# quebra quem consome.
CLIENT_FIELDS = {"client_key", "party_key", "status", "platform_fee_percentage"}

# A chave pública é UUID v4 em texto, gerada pelo Cadastro (01b §0.3).
UUID_V4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

ERROR_FIELDS = {"title", "description", "translation", "code"}

PLATFORM_PARTY_KEY = "99999999-9999-4999-8999-999999999999"
PLATFORM_CLIENT_KEY = "9c9c9c9c-9c9c-49c9-89c9-9c9c9c9c9c9c"
NOT_FOUND_PARTY_KEY = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


class _Absent:
    """Marca "campo ausente" nos casos de schema: None é o null do JSON."""

    def __repr__(self) -> str:
        return "<ausente>"


ABSENT = _Absent()


class TestClientCreate:
    def test_post_clients_pj_active_vira_cliente(self):
        """CU-P6: uma pessoa jurídica aprovada pelo bureau vira cliente.

        O 201 traz o mesmo corpo do GET do cliente, e a parte passa a dizer,
        no GET /parties/{key}, qual é o cliente dela (01b §1).
        """
        party_key = ObjectGenerator.create_organization_party()["party_key"]
        payload = PayloadGenerator.create_client_payload(party_key)

        status, response = RequestGenerator.POST_client(payload)
        assert status == 201
        assert set(response.keys()) == CLIENT_FIELDS
        assert UUID_V4.match(response["client_key"])
        assert response["party_key"] == party_key
        assert response["status"] == "active"
        assert response["platform_fee_percentage"] == "1.0000"

        created_client = response

        status, response = RequestGenerator.GET_client(created_client["client_key"])
        assert status == 200
        assert response == created_client

        status, response = RequestGenerator.GET_party(party_key)
        assert status == 200
        assert response["client_key"] == created_client["client_key"]

    @pytest.mark.parametrize("ending", [None, "00"], ids=["pf_active", "pf_rejected"])
    def test_post_clients_pessoa_fisica_devolve_422(self, ending):
        """CU-P7: pessoa física não vira cliente, em estado nenhum.

        Ser PF é defeito permanente; o estado pode mudar. Por isso a PF
        recusada pelo bureau recebe 422, e não o 409 de "não está ativa"
        (sumário L13).
        """
        party_payload = PayloadGenerator.create_party_payload(
            document_number=RandomGenerator.generate_cpf_digits(ending)
        )
        party_key = ObjectGenerator.create_party(party_payload)["party_key"]

        status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(party_key))

        assert status == 422
        assert set(response.keys()) == ERROR_FIELDS
        assert response["code"] == "QIT002006"
        assert party_key in response["description"]
        assert RequestGenerator.GET_party(party_key)[1]["client_key"] is None

    @pytest.mark.parametrize(
        "ending, expected_status",
        [("99", "pending"), ("00", "rejected")],
        ids=["pj_pending", "pj_rejected"],
    )
    def test_post_clients_parte_nao_active_devolve_409(self, ending, expected_status):
        """Só pessoa jurídica ativa vira cliente: pending (o bureau não
        respondeu) e rejected ficam de fora, com 409 e nada gravado."""
        party = ObjectGenerator.create_organization_party(ending)
        assert party["status"] == expected_status

        status, response = RequestGenerator.POST_client(
            PayloadGenerator.create_client_payload(party["party_key"])
        )

        assert status == 409
        assert set(response.keys()) == ERROR_FIELDS
        assert response["code"] == "QIT002008"
        assert RequestGenerator.GET_party(party["party_key"])[1]["client_key"] is None

    def test_post_clients_parte_inexistente_devolve_404(self):
        status, response = RequestGenerator.POST_client(
            PayloadGenerator.create_client_payload(NOT_FOUND_PARTY_KEY)
        )

        assert status == 404
        assert set(response.keys()) == ERROR_FIELDS
        assert response["code"] == "QIT002001"
        assert NOT_FOUND_PARTY_KEY in response["description"]

    @pytest.mark.parametrize("who", ["pj_criada", "plataforma"])
    def test_post_clients_parte_ja_cliente_devolve_409(self, who):
        """Uma parte, um cliente (RFC: "idempotente: uma por parte").

        Repetir, mesmo com outro percentual, não cria um segundo cliente nem
        muda o preço do primeiro. Quem decide é a UNIQUE(party_id) do banco.
        """
        if who == "plataforma":
            party_key = PLATFORM_PARTY_KEY
            client_key = PLATFORM_CLIENT_KEY
            previous_percentage = "0.0000"
        else:
            party_key = ObjectGenerator.create_organization_party()["party_key"]
            status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(party_key))
            assert status == 201
            client_key = response["client_key"]
            previous_percentage = "1.0000"

        status, response = RequestGenerator.POST_client(
            PayloadGenerator.create_client_payload(party_key, platform_fee_percentage="10.0000")
        )

        assert status == 409
        assert set(response.keys()) == ERROR_FIELDS
        assert response["code"] == "QIT002007"

        status, response = RequestGenerator.GET_client(client_key)
        assert status == 200
        assert response["platform_fee_percentage"] == previous_percentage

    @pytest.mark.parametrize(
        "field, value",
        [
            ("actor", ABSENT),
            ("actor", ""),
            ("party_key", ABSENT),
            ("party_key", "1111…"),
            ("platform_fee_percentage", ABSENT),
            ("platform_fee_percentage", 1.0),
            ("platform_fee_percentage", "100.0000"),
            ("platform_fee_percentage", "1.00000"),
            ("platform_fee_percentage", "-1.0000"),
            ("platform_fee_percentage", None),
            ("platform_fee_percentage", "١.0000"),
            ("campo_que_nao_existe", 1),
        ],
        ids=[
            "sem_actor",
            "actor_vazio",
            "sem_party_key",
            "party_key_abreviada",
            "sem_percentual",
            "percentual_numero",
            "percentual_100",
            "percentual_cinco_casas",
            "percentual_negativo",
            "percentual_nulo",
            "percentual_digitos_unicode",
            "campo_desconhecido",
        ],
    )
    def test_post_clients_corpo_fora_do_schema_devolve_400(self, field, value):
        """O schema recusa antes de o controller existir.

        A parte é uma PJ ativa de verdade: se o pedido passasse do schema,
        viraria cliente — então o único motivo possível do 400 é a forma.
        O percentual com dígito arábico-índico é o "1.0000" do guia §5
        escrito com outro 1: o `\\d` aceitaria, o `[0-9]` não (spec 04, P1).
        """
        party_key = ObjectGenerator.create_organization_party()["party_key"]
        payload = PayloadGenerator.create_client_payload(party_key)

        if value is ABSENT:
            del payload[field]
        else:
            payload[field] = value

        status, response = RequestGenerator.POST_client(payload)

        assert status == 400, f"o campo '{field}' aceitou o valor {value!r}"
        assert response["code"] == "QIT000001"

    @pytest.mark.parametrize(
        "field",
        ["party_key", "platform_fee_percentage"],
        ids=["party_key", "percentual"],
    )
    def test_post_clients_quebra_de_linha_no_fim_devolve_400(self, field):
        """Um `\\n` no fim não passa no schema (PAR-01).

        O `$` do `re` do Python casa antes de um `\\n` final. A parte é
        uma PJ ativa de verdade; a prova de que nada foi gravado é que o
        mesmo pedido, sem o `\\n`, ainda cria o cliente (e não dá 409).
        """
        party_key = ObjectGenerator.create_organization_party()["party_key"]
        payload = PayloadGenerator.create_client_payload(party_key)
        valid_payload = dict(payload)
        payload[field] = payload[field] + "\n"

        status, response = RequestGenerator.POST_client(payload)

        assert status == 400, f"o campo '{field}' aceitou o valor {payload[field]!r}"
        assert response["code"] == "QIT000001"

        status, response = RequestGenerator.POST_client(valid_payload)
        assert status == 201

    def test_post_clients_percentual_sai_com_quatro_casas(self):
        """O percentual sai com quatro casas mesmo que entre sem elas (01b §0.3).

        O 201 é montado antes do commit, com o valor que chegou; o GET lê o
        NUMERIC(7,4) do banco. Os dois têm de dizer a mesma coisa.
        """
        party_key = ObjectGenerator.create_organization_party()["party_key"]

        status, response = RequestGenerator.POST_client(
            PayloadGenerator.create_client_payload(party_key, platform_fee_percentage="1")
        )
        assert status == 201
        assert response["platform_fee_percentage"] == "1.0000"

        status, response = RequestGenerator.GET_client(response["client_key"])
        assert status == 200
        assert response["platform_fee_percentage"] == "1.0000"
