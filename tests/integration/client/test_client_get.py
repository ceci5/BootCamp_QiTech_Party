from tests.utils import RequestGenerator


PLATFORM_CLIENT_KEY = "9c9c9c9c-9c9c-49c9-89c9-9c9c9c9c9c9c"
PLATFORM_PARTY_KEY = "99999999-9999-4999-8999-999999999999"
NOT_FOUND_CLIENT_KEY = "c404c404-c404-4c40-8c40-c404c404c404"

ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestClientGet:
    def test_get_client_plataforma_semeada(self):
        """A plataforma é cliente dela mesma, e nasce com o banco (guia §4).

        O corpo inteiro é comparado: é o mesmo do mock que o Contrato usa
        (00 §2), e a fatia 05 confere os dois lado a lado.
        """
        status, response = RequestGenerator.GET_client(PLATFORM_CLIENT_KEY)
        assert status == 200
        assert response == {
            "client_key": PLATFORM_CLIENT_KEY,
            "party_key": PLATFORM_PARTY_KEY,
            "status": "active",
            "platform_fee_percentage": "0.0000",
        }

    def test_get_client_inexistente_devolve_404(self):
        status, response = RequestGenerator.GET_client(NOT_FOUND_CLIENT_KEY)
        assert status == 404
        assert set(response.keys()) == ERROR_FIELDS
        assert response["code"] == "QIT002005"
        assert NOT_FOUND_CLIENT_KEY in response["description"]
