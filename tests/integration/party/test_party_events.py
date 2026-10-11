import pytest

from tests.utils import BureauMock, DbUtils, PayloadGenerator, RequestGenerator


PLATFORM_PARTY_KEY = "99999999-9999-4999-8999-999999999999"

# O identificador do exemplo do 01b §1.
REQUEST_ID = "7b0e1f6c-ativacao-ctr-42"


class TestPartyEvents:
    @pytest.mark.parametrize("request_id", [None, REQUEST_ID], ids=["sem_header", "com_header"])
    def test_post_parties_eventos_carregam_o_x_request_id(self, request_id):
        """CU-P8: um só identificador amarra a resposta, a trilha e o bureau.

        Sem o cabeçalho, a API inventa um; com ele, reaproveita o de quem
        chamou. Nos dois casos, o número que o cliente recebe na resposta é
        o trace_id dos DOIS eventos e o X-Request-ID que chegou ao bureau.
        """
        payload = PayloadGenerator.create_party_payload()

        status, response, response_request_id = RequestGenerator.POST_party_with_request_id(
            payload, request_id
        )
        assert status == 201
        assert response_request_id is not None

        if request_id is not None:
            assert response_request_id == request_id

        events = DbUtils.party_status_events(response["party_key"])
        assert len(events) == 2
        assert events[0]["from_status"] is None
        assert [e["trace_id"] for e in events] == [response_request_id, response_request_id]

        assert BureauMock.received_request_ids(payload["document_number"]) == [response_request_id]

    @pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "TRUNCATE"])
    def test_party_status_event_recusa_update_delete_truncate(self, operation):
        """A trilha de estado é append-only no banco, não por combinado.

        Dois gatilhos: o de linha pega UPDATE e DELETE; o de comando pega
        TRUNCATE, que o de linha não vê. A parte usada é a plataforma
        semeada, que sempre tem um evento.
        """
        events_before = DbUtils.party_status_events(PLATFORM_PARTY_KEY)
        assert len(events_before) >= 1

        error_message = DbUtils.try_to_change_party_status_events(operation, PLATFORM_PARTY_KEY)
        assert error_message == "party_status_event e append-only"

        assert DbUtils.party_status_events(PLATFORM_PARTY_KEY) == events_before
