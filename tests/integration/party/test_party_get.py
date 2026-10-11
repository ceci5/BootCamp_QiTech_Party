import pytest

from tests.utils import ObjectGenerator, PayloadGenerator, RandomGenerator, RequestGenerator


PLATFORM_PARTY_KEY = "99999999-9999-4999-8999-999999999999"
NOT_FOUND_PARTY_KEY = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

# Os campos de GET /parties/{key} (01b §1). Os outros dois serviços leem
# esta rota: campo a mais ou a menos quebra quem consome.
PARTY_FIELDS = {"party_key", "party_type", "status", "pix_key", "client_key"}
ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestPartyGet:
    @pytest.mark.parametrize(
        "document_number, pix_key, party_type",
        [
            (RandomGenerator.generate_cpf_digits(), "ana.locadora@example.com", "individual"),
            (RandomGenerator.generate_cpf_digits(), "timeout@mock", "individual"),
            (RandomGenerator.generate_cnpj_digits(), None, "organization"),
        ],
        ids=["pf_com_pix", "pf_com_pix_do_mock", "pj_sem_pix"],
    )
    def test_get_party_devolve_so_os_campos_do_01b(self, document_number, pix_key, party_type):
        """Os cinco campos do contrato (01b §1), e nenhum dado pessoal.

        Nome e documento entram no POST e não saem nunca mais (D0008). O
        status não é conferido aqui: ele depende do bureau, e o assunto
        deste teste é a FORMA da resposta.
        """
        payload = PayloadGenerator.create_party_payload(document_number=document_number)
        if pix_key is None:
            del payload["pix_key"]
        else:
            payload["pix_key"] = pix_key

        party_key = ObjectGenerator.create_party(payload)["party_key"]

        status, response = RequestGenerator.GET_party(party_key)
        assert status == 200
        assert set(response.keys()) == PARTY_FIELDS
        assert response["party_key"] == party_key
        assert response["party_type"] == party_type
        assert response["status"] in {"pending", "active", "rejected"}
        assert response["pix_key"] == pix_key
        assert response["client_key"] is None
        assert payload["name"] not in response.values()
        assert document_number not in response.values()

    def test_get_party_inexistente_devolve_404(self):
        status, response = RequestGenerator.GET_party(NOT_FOUND_PARTY_KEY)
        assert status == 404
        assert set(response.keys()) == ERROR_FIELDS
        assert response["code"] == "QIT002001"
        assert NOT_FOUND_PARTY_KEY in response["description"]

    def test_get_party_plataforma_semeada(self):
        """A plataforma nasce com o banco (database.sql), não por POST.

        O client_key não é conferido aqui: quem o preenche é a fatia 04, e
        este teste não deve precisar mudar quando ela chegar.
        """
        status, response = RequestGenerator.GET_party(PLATFORM_PARTY_KEY)
        assert status == 200
        assert set(response.keys()) == PARTY_FIELDS
        assert response["party_key"] == PLATFORM_PARTY_KEY
        assert response["party_type"] == "organization"
        assert response["status"] == "active"
        assert response["pix_key"] == "plataforma@example.com"

    def test_get_party_plataforma_devolve_client_key(self):
        """A plataforma é cliente dela mesma (fatia 04): o GET da parte diz qual.

        O corpo inteiro é comparado com o do mock (00 §2), que é o que o
        Contrato e o Ledger esperam desta chave.
        """
        status, response = RequestGenerator.GET_party(PLATFORM_PARTY_KEY)
        assert status == 200
        assert response == {
            "party_key": PLATFORM_PARTY_KEY,
            "party_type": "organization",
            "status": "active",
            "pix_key": "plataforma@example.com",
            "client_key": "9c9c9c9c-9c9c-49c9-89c9-9c9c9c9c9c9c",
        }
