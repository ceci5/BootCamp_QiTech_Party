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
    def POST_party(party_payload: dict) -> tuple:
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
    def GET_party(party_key: str) -> tuple:
        response = ClientRequisition.send(
            "GET",
            f"/parties/{party_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def POST_client(client_payload: dict) -> tuple:
        response = ClientRequisition.send(
            "POST",
            "/clients",
            payload=client_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def GET_client(client_key: str) -> tuple:
        response = ClientRequisition.send(
            "GET",
            f"/clients/{client_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def GET_party_with_request_id(party_key: str, request_id: str) -> tuple:
        """Como o GET_party, com X-Request-ID; devolve também o da resposta (01b §0.1)."""
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN, "X-Request-ID": request_id}
        response = ClientRequisition.send("GET", f"/parties/{party_key}", headers=headers)
        return response.response_status, response.response_json, response.response.headers.get("X-Request-ID")

    @staticmethod
    def GET_client_with_request_id(client_key: str, request_id: str) -> tuple:
        """Como o GET_client, com X-Request-ID; devolve também o da resposta (01b §0.1)."""
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN, "X-Request-ID": request_id}
        response = ClientRequisition.send("GET", f"/clients/{client_key}", headers=headers)
        return response.response_status, response.response_json, response.response.headers.get("X-Request-ID")

    @staticmethod
    def GET_party_with_content_type(party_key: str) -> tuple:
        """Como o GET_party; devolve também o Content-Type da resposta (spec 05, CA-13)."""
        response = ClientRequisition.send("GET", f"/parties/{party_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        return response.response_status, response.response_json, response.response.headers.get("Content-Type")

    @staticmethod
    def GET_client_with_content_type(client_key: str) -> tuple:
        """Como o GET_client; devolve também o Content-Type da resposta (spec 05, CA-14)."""
        response = ClientRequisition.send("GET", f"/clients/{client_key}", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
        return response.response_status, response.response_json, response.response.headers.get("Content-Type")

    @staticmethod
    def POST_party_verification(party_key: str, verification_payload: dict) -> tuple:
        """Repescagem do bureau (spec 06). Com `verification_payload=None`, vai sem corpo."""
        response = ClientRequisition.send(
            "POST",
            f"/parties/{party_key}/verification",
            payload=verification_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def POST_party_verification_with_request_id(
        party_key: str, verification_payload: dict, request_id: str = None
    ) -> tuple:
        """Como o POST_party_verification, devolvendo também o X-Request-ID DA RESPOSTA.

        É o número que tem de aparecer no trace_id do evento da repescagem e
        no bureau (spec 06, CA-02). Se `request_id` vier, vai no cabeçalho.
        """
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        if request_id is not None:
            headers["X-Request-ID"] = request_id

        response = ClientRequisition.send(
            "POST", f"/parties/{party_key}/verification", payload=verification_payload, headers=headers
        )
        return response.response_status, response.response_json, response.response.headers.get("X-Request-ID")

    @staticmethod
    def GET_parties(params: dict = None) -> tuple:
        """Busca por documento (spec 07): `params` vira a query string."""
        response = ClientRequisition.send(
            "GET", "/parties", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}, query_params=params
        )
        return response.response_status, response.response_json
