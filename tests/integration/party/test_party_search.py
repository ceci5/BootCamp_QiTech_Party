import pytest

from tests.utils import ObjectGenerator, PayloadGenerator, RandomGenerator, RequestGenerator
from tests.utils.requisition import ClientRequisition


# A plataforma semeada no database.sql (guia §4; 00 §2).
PLATFORM_PARTY_KEY = "99999999-9999-4999-8999-999999999999"
PLATFORM_DOCUMENT_NUMBER = "11222333000181"


class TestPartySearch:
    @pytest.mark.parametrize(
        "document_number",
        [RandomGenerator.generate_cpf_digits(), RandomGenerator.generate_cnpj_digits()],
        ids=["pf", "pj"],
    )
    def test_get_parties_por_documento_devolve_a_parte(self, document_number):
        """O ERP recupera a chave pelo documento (spec 07, CA-01).

        A resposta tem só a chave e o estado: o documento já é de quem
        pergunta, e nome nem documento saem do Cadastro (D0008).
        """
        payload = PayloadGenerator.create_party_payload(document_number=document_number)
        created = ObjectGenerator.create_party(payload)

        status, response = RequestGenerator.GET_parties({"document_number": document_number})

        assert status == 200
        assert set(response.keys()) == {"data"}
        assert len(response["data"]) == 1
        assert set(response["data"][0].keys()) == {"party_key", "status"}
        assert response["data"][0]["party_key"] == created["party_key"]
        assert response["data"][0]["status"] == "active"
        assert payload["name"] not in response["data"][0].values()
        assert document_number not in response["data"][0].values()

    @pytest.mark.parametrize(
        "ending, expected_status",
        [("00", "rejected"), ("99", "pending")],
        ids=["rejected", "pending"],
    )
    def test_get_parties_devolve_o_estado_atual(self, ending, expected_status):
        """O estado de agora, não só `active` (spec 07, CA-02).

        O bureau mockado decide pelo final: `00` recusa, `99` não responde.
        """
        document_number = RandomGenerator.generate_cpf_digits(ending)
        payload = PayloadGenerator.create_party_payload(document_number=document_number)
        created = ObjectGenerator.create_party(payload)
        assert created["status"] == expected_status

        status, response = RequestGenerator.GET_parties({"document_number": document_number})

        assert status == 200
        assert response == {"data": [{"party_key": created["party_key"], "status": expected_status}]}

    def test_get_parties_plataforma_semeada(self):
        """A plataforma nasce com o banco, não por POST (spec 07, CA-03)."""
        status, response = RequestGenerator.GET_parties({"document_number": PLATFORM_DOCUMENT_NUMBER})

        assert status == 200
        assert response == {"data": [{"party_key": PLATFORM_PARTY_KEY, "status": "active"}]}

    @pytest.mark.parametrize(
        "document_number",
        [RandomGenerator.generate_cpf_digits(), RandomGenerator.generate_invalid_cpf_digits()],
        ids=["nao_cadastrado", "digitos_invalidos"],
    )
    def test_get_parties_documento_sem_parte_devolve_lista_vazia(self, document_number):
        """Ninguém tem o documento: lista vazia, nem 404 nem 422 (spec 07, CA-04, RN-03)."""
        status, response = RequestGenerator.GET_parties({"document_number": document_number})

        assert status == 200
        assert response == {"data": []}

    @pytest.mark.parametrize(
        "params",
        [
            None,
            {"document_number": ""},
            {"document_number": "123.456.789-09"},
            {"document_number": "1234567890"},
            {"document_number": "123456780001950"},
            {"document_number": "1234567890a"},
            {"document_number": "１２３４５６７８９０９"},
            {"document_number": "12345678909", "name": "Ana Souza"},
        ],
        ids=[
            "sem_parametro",
            "vazio",
            "com_mascara",
            "com_10_digitos",
            "com_15_digitos",
            "com_letra",
            "digitos_unicode",
            "parametro_desconhecido",
        ],
    )
    def test_get_parties_query_fora_do_schema_devolve_400(self, params):
        """O schema recusa antes de qualquer consulta (spec 07, CA-05, RN-02).

        Os valores derivam do `12345678909` e da `Ana Souza` do guia §5 e do
        `12345678000195` do 01b; cada caso muda uma coisa só. Os dígitos de
        largura total provam o `[0-9]` no lugar do `\\d` (sumário L3).
        """
        status, response = RequestGenerator.GET_parties(params)

        assert status == 400, f"a query {params!r} foi aceita"
        assert response["code"] == "QIT000001"

    def test_get_parties_sem_internal_token_devolve_403(self):
        """A busca por documento não é pública (spec 07, CA-06, RN-01)."""
        response = ClientRequisition.send(
            "GET", "/parties", query_params={"document_number": PLATFORM_DOCUMENT_NUMBER}
        )

        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
