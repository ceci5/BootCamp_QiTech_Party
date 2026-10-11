import pytest
from jsonschema import validate

from tests.utils import ObjectGenerator, PartyApiMocks, PayloadGenerator, RandomGenerator, RequestGenerator


# O teste do dono (00 §1, regra 2): os mocks que o Cadastro publica para o
# Contrato e o Ledger (docs/mocks/party-api/, copiados em tests/mocks/) têm
# a forma do 01b, e a API real responde igual a eles. Se este arquivo passa
# e o consumidor passa contra o mock, os dois concordam. Mudou o contrato?
# Muda o mock nos docs, recopia, e avisa os outros dois (01b §9) — nunca se
# "conserta" a cópia nem este teste sozinho.

UUID_V4_PATTERN = "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"

# Os schemas de resposta (spec 02 §3.3, versão R9). O additionalProperties
# False é o "exatamente os campos do 01b": campo a mais (um nome, um
# documento) reprova. Sem "format": o jsonschema não o valida.
GET_PARTY_RESPONSE = {
    "title": "GetPartyResponse",
    "type": "object",
    "properties": {
        "party_key": {"type": "string", "pattern": UUID_V4_PATTERN},
        "party_type": {"type": "string", "enum": ["individual", "organization"]},
        "status": {"type": "string", "enum": ["pending", "active", "rejected"]},
        "pix_key": {
            "type": ["string", "null"],
            "maxLength": 77,
            "pattern": "^([^@\\s]+@[^@\\s]+|\\+55[0-9]{10,11}|[0-9]{11}|[0-9]{14}"
            "|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
        },
        "client_key": {"type": ["string", "null"], "pattern": UUID_V4_PATTERN},
    },
    "required": ["party_key", "party_type", "status", "pix_key", "client_key"],
    "additionalProperties": False,
}

GET_CLIENT_RESPONSE = {
    "title": "GetClientResponse",
    "type": "object",
    "properties": {
        "client_key": {"type": "string", "pattern": UUID_V4_PATTERN},
        "party_key": {"type": "string", "pattern": UUID_V4_PATTERN},
        "status": {"type": "string", "enum": ["pending", "active", "rejected"]},
        "platform_fee_percentage": {"type": "string", "pattern": "^[0-9]{1,2}\\.[0-9]{4}$"},
    },
    "required": ["client_key", "party_key", "status", "platform_fee_percentage"],
    "additionalProperties": False,
}

ERROR_RESPONSE = {
    "title": "ErrorResponse",
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "translation": {"type": "string", "minLength": 1},
        "code": {"type": "string", "pattern": "^QIT[0-9]{6}$"},
    },
    "required": ["title", "description", "translation", "code"],
    "additionalProperties": False,
}

# As chaves mágicas (00 §2). A parametrização sai destas listas, nunca da
# pasta: com a cópia vazia, um parametrize sobre a pasta daria zero itens,
# e o pytest diria "skipped" em vez de "failed".
PLATFORM_PARTY_KEY = "99999999-9999-4999-8999-999999999999"
NOT_FOUND_PARTY_KEY = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
OFFLINE_PARTY_KEY = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

PLATFORM_CLIENT_KEY = "9c9c9c9c-9c9c-49c9-89c9-9c9c9c9c9c9c"
NOT_FOUND_CLIENT_KEY = "c404c404-c404-4c40-8c40-c404c404c404"
OFFLINE_CLIENT_KEY = "c503c503-c503-4c50-8c50-c503c503c503"

CLIENT_KEYS_200 = {
    "alfa": "c1c1c1c1-c1c1-4c1c-8c1c-c1c1c1c1c1c1",
    "plataforma": PLATFORM_CLIENT_KEY,
}

# O X-Request-ID do exemplo do 01b §1.
EXAMPLE_REQUEST_ID = "7b0e1f6c-ativacao-ctr-42"

# Os pega-tudo do mock (sumário L2): chave fora da tabela vira 404.
CATCH_ALL_PARTIES = "/parties/.*"
CATCH_ALL_CLIENTS = "/clients/.*"

# As partes que o mock devolve com 200, com o nome do caso no pytest.
PARTY_KEYS_200 = {
    "alfa": "11111111-1111-4111-8111-111111111111",
    "ana": "22222222-2222-4222-8222-222222222222",
    "bruno": "33333333-3333-4333-8333-333333333333",
    "prefeitura": "44444444-4444-4444-8444-444444444444",
    "condominio": "55555555-5555-4555-8555-555555555555",
    "agua": "66666666-6666-4666-8666-666666666666",
    "luz": "77777777-7777-4777-8777-777777777777",
    "carlos": "88888888-8888-4888-8888-888888888888",
    "plataforma": PLATFORM_PARTY_KEY,
    "pendente": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "sem_pix": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    "pix_timeout": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    "pix_erro": "ffffffff-ffff-4fff-8fff-ffffffffffff",
}

# A semente é comparada inteira (CA-06); as outras nascem por POST (CA-04).
CREATED_PARTY_CASES = {name: key for name, key in PARTY_KEYS_200.items() if key != PLATFORM_PARTY_KEY}

# O final do documento que faz o bureau mockado dar cada estado (00 §2).
ENDING_FOR_STATUS = {"active": None, "pending": "99", "rejected": "00"}


def mock_response(url_path: str) -> dict:
    """A resposta do único mapping deste caminho na cópia."""
    mappings = PartyApiMocks.by_url_path(url_path)
    assert len(mappings) == 1, f"{url_path}: {len(mappings)} mappings na cópia, esperado 1"
    return mappings[0]["response"]


def create_party_like(mock_body: dict) -> dict:
    """Cria por POST a parte real que o mock descreve (spec 05, RN-04).

    Tipo, pix_key e estado vêm do mapping; o documento é sorteado com o
    final que leva o bureau ao mesmo estado. Se a parte do mock é cliente,
    ela vira cliente com o percentual do mapping desse cliente. Devolve as
    chaves reais, para trocar pelas do mock na comparação.
    """
    ending = ENDING_FOR_STATUS[mock_body["status"]]
    if mock_body["party_type"] == "individual":
        document_number = RandomGenerator.generate_cpf_digits(ending)
    else:
        document_number = RandomGenerator.generate_cnpj_digits(ending)

    payload = PayloadGenerator.create_party_payload(document_number=document_number)
    if mock_body["pix_key"] is None:
        del payload["pix_key"]
    else:
        payload["pix_key"] = mock_body["pix_key"]

    real_keys = {"party_key": ObjectGenerator.create_party(payload)["party_key"], "client_key": None}

    if mock_body["client_key"] is not None:
        mock_client = mock_response(f"/clients/{mock_body['client_key']}")["jsonBody"]
        client = ObjectGenerator.create_client(real_keys["party_key"], mock_client["platform_fee_percentage"])
        real_keys["client_key"] = client["client_key"]

    return real_keys


class TestContrato01bMocks:
    def test_mocks_copia_tem_um_mapping_por_chave_magica(self):
        """CA-01: a cópia tem um mapping por chave do 00 §2, mais os dois pega-tudo.

        São 15 partes + 4 clientes + 2 pega-tudo = 21 (spec 02, INV-01). Os
        dois "fora do ar" só se conferem aqui: a API real não tem como ficar
        fora do ar sob comando (spec 05, RN-07).
        """
        assert len(PartyApiMocks.mappings()) == 21

        party_keys = [*PARTY_KEYS_200.values(), NOT_FOUND_PARTY_KEY, OFFLINE_PARTY_KEY]
        client_keys = [*CLIENT_KEYS_200.values(), NOT_FOUND_CLIENT_KEY, OFFLINE_CLIENT_KEY]
        url_paths = [f"/parties/{key}" for key in party_keys] + [f"/clients/{key}" for key in client_keys]
        for url_path in url_paths:
            mappings = PartyApiMocks.by_url_path(url_path)
            assert len(mappings) == 1, f"{url_path}: {len(mappings)} mappings"
            assert mappings[0]["request"]["method"] == "GET"

        for pattern in (CATCH_ALL_PARTIES, CATCH_ALL_CLIENTS):
            catch_all = PartyApiMocks.by_url_path_pattern(pattern)
            assert len(catch_all) == 1, f"{pattern}: {len(catch_all)} mappings"
            assert catch_all[0]["response"]["status"] == 404

        for key in (f"/parties/{OFFLINE_PARTY_KEY}", f"/clients/{OFFLINE_CLIENT_KEY}"):
            offline = mock_response(key)
            assert offline["status"] == 503
            assert offline["fixedDelayMilliseconds"] == 2000

    @pytest.mark.parametrize("party_key", PARTY_KEYS_200.values(), ids=PARTY_KEYS_200.keys())
    def test_get_party_mock_200_segue_o_schema_do_01b(self, party_key):
        """CA-02: toda parte que o mock devolve tem exatamente os campos do 01b §1."""
        response = mock_response(f"/parties/{party_key}")
        assert response["status"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        validate(response["jsonBody"], GET_PARTY_RESPONSE)
        assert response["jsonBody"]["party_key"] == party_key

    @pytest.mark.parametrize("client_key", CLIENT_KEYS_200.values(), ids=CLIENT_KEYS_200.keys())
    def test_get_client_mock_200_segue_o_schema_do_01b(self, client_key):
        """CA-03: todo cliente do mock tem os campos do 01b §2, e a parte dele aponta de volta."""
        response = mock_response(f"/clients/{client_key}")
        assert response["status"] == 200
        validate(response["jsonBody"], GET_CLIENT_RESPONSE)
        assert response["jsonBody"]["client_key"] == client_key

        party = mock_response(f"/parties/{response['jsonBody']['party_key']}")["jsonBody"]
        assert party["client_key"] == client_key


class TestContrato01bGetParty:
    @pytest.mark.parametrize("mock_party_key", CREATED_PARTY_CASES.values(), ids=CREATED_PARTY_CASES.keys())
    def test_get_party_real_reproduz_o_mock(self, mock_party_key):
        """CA-04: a parte que o mock descreve, criada de verdade, responde igual ao mock.

        As chaves mágicas só existem no mock (sumário L10): o lado real
        nasce por POST, e a comparação troca as chaves do mock pelas reais.
        """
        mock_body = mock_response(f"/parties/{mock_party_key}")["jsonBody"]
        real_keys = create_party_like(mock_body)

        status, response = RequestGenerator.GET_party(real_keys["party_key"])
        assert status == 200
        validate(response, GET_PARTY_RESPONSE)
        assert response == {**mock_body, **real_keys}

    def test_get_party_real_rejected_segue_o_schema_do_01b(self):
        """CA-05: o "rejected" do enum do 01b §1, que nenhum mapping usa, sai com os mesmos campos."""
        payload = PayloadGenerator.create_party_payload(document_number=RandomGenerator.generate_cpf_digits("00"))
        party_key = ObjectGenerator.create_party(payload)["party_key"]

        status, response = RequestGenerator.GET_party(party_key)
        assert status == 200
        validate(response, GET_PARTY_RESPONSE)
        assert response["status"] == "rejected"
        assert set(response.keys()) == set(mock_response(f"/parties/{PARTY_KEYS_200['ana']}")["jsonBody"].keys())

    def test_get_party_plataforma_igual_ao_mock(self):
        """CA-06: a plataforma semeada é, campo a campo, a do mock (G §13).

        O esperado vem do arquivo, não de um literal: é isso que acusa mock e
        API divergindo.
        """
        status, response = RequestGenerator.GET_party(PLATFORM_PARTY_KEY)
        assert status == 200
        assert response == mock_response(f"/parties/{PLATFORM_PARTY_KEY}")["jsonBody"]

    @pytest.mark.parametrize(
        "mock_error",
        [
            lambda: mock_response(f"/parties/{NOT_FOUND_PARTY_KEY}"),
            lambda: PartyApiMocks.by_url_path_pattern(CATCH_ALL_PARTIES)[0]["response"],
        ],
        ids=["bbbb", "pega_tudo"],
    )
    def test_get_party_404_igual_ao_mock(self, mock_error):
        """CA-07: parte inexistente tem o mesmo 404 no mock e na API real.

        Compara status, chaves e code; o texto não (o pega-tudo do mock usa
        template, e a spec 02 não fixa o texto para os consumidores).
        """
        mock = mock_error()
        status, response = RequestGenerator.GET_party(NOT_FOUND_PARTY_KEY)
        validate(mock["jsonBody"], ERROR_RESPONSE)
        validate(response, ERROR_RESPONSE)
        assert status == mock["status"] == 404
        assert set(response.keys()) == set(mock["jsonBody"].keys())
        assert response["code"] == mock["jsonBody"]["code"] == "QIT002001"
        assert NOT_FOUND_PARTY_KEY in response["description"]

    def test_get_party_exemplo_do_01b_devolve_o_x_request_id(self):
        """CA-08: a requisição do exemplo do 01b §1, literal, contra a API real.

        A 2222… só existe no mock (sumário L10): no real é 404. O que se
        prova é o código e que o X-Request-ID volta igual (01b §0.1).
        """
        party_key = PARTY_KEYS_200["ana"]
        status, response, request_id = RequestGenerator.GET_party_with_request_id(party_key, EXAMPLE_REQUEST_ID)
        assert status == 404
        validate(response, ERROR_RESPONSE)
        assert response["code"] == "QIT002001"
        assert request_id == EXAMPLE_REQUEST_ID


class TestContrato01bGetClient:
    def test_get_client_plataforma_igual_ao_mock(self):
        """CA-10: o cliente semeado da plataforma é, campo a campo, o do mock (G §13)."""
        status, response = RequestGenerator.GET_client(PLATFORM_CLIENT_KEY)
        assert status == 200
        assert response == mock_response(f"/clients/{PLATFORM_CLIENT_KEY}")["jsonBody"]

    @pytest.mark.parametrize(
        "mock_error",
        [
            lambda: mock_response(f"/clients/{NOT_FOUND_CLIENT_KEY}"),
            lambda: PartyApiMocks.by_url_path_pattern(CATCH_ALL_CLIENTS)[0]["response"],
        ],
        ids=["c404", "pega_tudo"],
    )
    def test_get_client_404_igual_ao_mock(self, mock_error):
        """CA-11: cliente inexistente tem o mesmo 404 no mock e na API real."""
        mock = mock_error()
        status, response = RequestGenerator.GET_client(NOT_FOUND_CLIENT_KEY)
        validate(mock["jsonBody"], ERROR_RESPONSE)
        validate(response, ERROR_RESPONSE)
        assert status == mock["status"] == 404
        assert set(response.keys()) == set(mock["jsonBody"].keys())
        assert response["code"] == mock["jsonBody"]["code"] == "QIT002005"
        assert NOT_FOUND_CLIENT_KEY in response["description"]

    def test_get_client_real_reproduz_o_mock(self):
        """CA-09: o cliente que o mock descreve (c1c1…, a Alfa), criado de verdade, responde igual."""
        mock_client = mock_response(f"/clients/{CLIENT_KEYS_200['alfa']}")["jsonBody"]
        mock_party = mock_response(f"/parties/{mock_client['party_key']}")["jsonBody"]
        real_keys = create_party_like(mock_party)

        status, response = RequestGenerator.GET_client(real_keys["client_key"])
        assert status == 200
        validate(response, GET_CLIENT_RESPONSE)
        assert response == {**mock_client, **real_keys}

    def test_get_client_exemplo_do_01b_devolve_o_x_request_id(self):
        """CA-12: GET /clients/c1c1… com os cabeçalhos do 01b; no real é 404 (sumário L10)."""
        client_key = CLIENT_KEYS_200["alfa"]
        status, response, request_id = RequestGenerator.GET_client_with_request_id(client_key, EXAMPLE_REQUEST_ID)
        assert status == 404
        validate(response, ERROR_RESPONSE)
        assert response["code"] == "QIT002005"
        assert request_id == EXAMPLE_REQUEST_ID
