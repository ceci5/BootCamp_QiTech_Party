from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ClientController
from utils.schema_handler import SchemaHandler


class ClientResource:
    """A porta de entrada HTTP do cliente da plataforma.

    O mesmo desenho do PartyResource: confere o formato, chama o
    controller, devolve com o status certo — e nada mais. Sem `raise`,
    sem SQL, sem `self.alguma_coisa`.
    """

    @SchemaHandler.validate("post_client.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = ClientController()
        client = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(client),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_by_key(self, client_key: str) -> JSONResponse:
        controller = ClientController()
        client = controller.get_by_key(client_key)

        return JSONResponse(
            content=jsonable_encoder(client),
            status_code=http_status.HTTP_200_OK,
        )
