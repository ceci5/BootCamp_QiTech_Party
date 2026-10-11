from os import environ

from tests.utils.requisition import ClientRequisition, BaseConnectorResponse


INTERNAL_TOKEN = environ.get("INTERNAL_TOKEN", "default_token")


class RequestGenerator:
    @staticmethod
    def POST_sample_entity(sample_entity_payload: dict) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/sample_entity",
            payload=sample_entity_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        return response.response_status, response.response_json

    @staticmethod
    def GET_sample_entity(sample_entity_key: str) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET",
            f"/sample_entity/{sample_entity_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def PUT_sample_entity(sample_entity_key: str, update_payload: dict) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "PUT",
            f"/sample_entity/{sample_entity_key}",
            payload=update_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def PUT_webhook_sample_entity(sample_entity_key: str) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "PUT",
            f"/webhook/sample_entity/{sample_entity_key}/increment_counter",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def GET_sample_entities(params: dict = None) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET", "/sample_entities", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}, query_params=params
        )
        return response.response_status, response.response_json

    @staticmethod
    def POST_party(party_payload: dict) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/parties",
            payload=party_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def POST_party_with_request_id(party_payload: dict, request_id: str = None) -> tuple:
        """Como o POST_party, devolvendo também o X-Request-ID DA RESPOSTA.

        É o número que tem de aparecer no trace_id dos eventos e no bureau
        (CU-P8). Se `request_id` vier, ele vai no cabeçalho da requisição.
        """
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        if request_id is not None:
            headers["X-Request-ID"] = request_id

        response = ClientRequisition.send("POST", "/parties", payload=party_payload, headers=headers)
        return response.response_status, response.response_json, response.response.headers.get("X-Request-ID")

    @staticmethod
    def GET_party(party_key: str) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET",
            f"/parties/{party_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def POST_client(client_payload: dict) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/clients",
            payload=client_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def GET_client(client_key: str) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET",
            f"/clients/{client_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json
