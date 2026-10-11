from os import environ

from requests import request
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout

from tests.utils.requisition import BaseConnectorResponse


# A porta do bureau-mock e fixa no compose ("8081:8080", 01b §0.2): nao vem do .env.
BUREAU_MOCK_PORT = "8081"

BUREAU_MOCK_OFFLINE = (
    "Não consegui falar com o bureau-mock em {base_url}.\n"
    "Ele precisa estar de pé pros testes rodarem. Suba com:  docker compose up"
)


class BureauMock:
    """Fala direto com o bureau-mock (WireMock), sem passar pela API.

    O `ClientRequisition` monta a URL pela API_PORT e não alcança a 8081.
    Serve para provar os mappings do bureau e para zerar o scenario
    `bureau-instavel` (documento terminado em 98) antes de quem o usa.
    """

    @staticmethod
    def _send(method: str, endpoint: str, payload: dict = None, timeout: float = None):
        api_host = environ.get("SERVER_LOCALHOST", "0.0.0.0")
        base_url = f"http://{api_host}:{BUREAU_MOCK_PORT}"

        try:
            response = request(method, f"{base_url}{endpoint}", json=payload, timeout=timeout)
        except RequestsConnectionError:
            raise RuntimeError(BUREAU_MOCK_OFFLINE.format(base_url=base_url)) from None

        return BaseConnectorResponse(
            endpoint=endpoint,
            method=method,
            payload=payload,
            headers={},
            response=response,
        )

    @staticmethod
    def POST_verifications(document_number: str, timeout: float) -> tuple:
        """Devolve (status, json); (None, None) se o mock passar do timeout."""
        try:
            response = BureauMock._send("POST", "/verifications", {"document_number": document_number}, timeout)
        except Timeout:
            return None, None

        return response.response_status, response.response_json

    @staticmethod
    def reset_scenarios() -> int:
        return BureauMock._send("POST", "/__admin/scenarios/reset").response_status

    @staticmethod
    def mappings_total() -> int:
        return BureauMock._send("GET", "/__admin/mappings").response_json["meta"]["total"]

    @staticmethod
    def received_request_ids(document_number: str) -> list:
        """O X-Request-ID de cada POST /verifications que o mock recebeu com este documento.

        Lê o diário de requisições do WireMock. Serve para provar duas
        coisas: que a API chamou o bureau, e que mandou o mesmo
        identificador que devolveu ao cliente (01b §0.1).
        """
        request_pattern = {
            "method": "POST",
            "url": "/verifications",
            "bodyPatterns": [
                {"matchesJsonPath": {"expression": "$.document_number", "equalTo": document_number}}
            ],
        }
        response = BureauMock._send("POST", "/__admin/requests/find", request_pattern)

        return [logged["headers"].get("X-Request-ID") for logged in response.response_json["requests"]]
