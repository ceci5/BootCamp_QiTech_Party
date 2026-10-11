from fastapi import Request
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

    @SchemaHandler.validate("post_party_verification.json")
    def on_post_verification(self, party_key: str, payload: dict) -> JSONResponse:
        # 200, e não 201: nada é criado. A resposta traz o estado depois da
        # tentativa, inclusive se continuou pending (guia §5).
        controller = PartyController()
        party = controller.verify(party_key, payload["actor"])

        return JSONResponse(
            content=jsonable_encoder(party),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate_query_params("get_parties.json")
    def on_get_list(self, request: Request) -> JSONResponse:
        """A busca por documento (spec 07): zero ou uma parte.

        O decorator já conferiu a query contra o get_parties.json, e o
        schema exige o document_number: por isso o acesso direto, sem
        `.get`. O envelope `data` é montado aqui, como no
        SampleEntityResource.on_get_list.
        """
        controller = PartyController()
        parties_list = controller.get_list(request.query_params["document_number"])

        return JSONResponse(
            content=jsonable_encoder({"data": parties_list}),
            status_code=http_status.HTTP_200_OK,
        )

    def on_get_by_key(self, party_key: str) -> JSONResponse:
        controller = PartyController()
        party = controller.get_by_key(party_key)

        return JSONResponse(
            content=jsonable_encoder(party),
            status_code=http_status.HTTP_200_OK,
        )
