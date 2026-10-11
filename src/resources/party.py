from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PartyController
from utils.schema_handler import SchemaHandler


class PartyResource:
    """A porta de entrada HTTP da parte (o Cadastro).

    O mesmo desenho do SampleEntityResource: confere o formato, chama o
    controller, devolve com o status certo — e nada mais. Sem `raise`,
    sem SQL, sem `self.alguma_coisa` (um resource só, para todas as
    requisições).
    """

    @SchemaHandler.validate("post_party.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = PartyController()
        party = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(party),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_by_key(self, party_key: str) -> JSONResponse:
        controller = PartyController()
        party = controller.get_by_key(party_key)

        return JSONResponse(
            content=jsonable_encoder(party),
            status_code=http_status.HTTP_200_OK,
        )
