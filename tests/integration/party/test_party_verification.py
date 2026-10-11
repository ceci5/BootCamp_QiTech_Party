import threading
import time

import pytest

from tests.utils import BureauMock, DbUtils, PayloadGenerator, RandomGenerator, RequestGenerator


PLATFORM_PARTY_KEY = "99999999-9999-4999-8999-999999999999"
PLATFORM_DOCUMENT_NUMBER = "11222333000181"
NOT_FOUND_PARTY_KEY = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

ERROR_FIELDS = {"title", "description", "translation", "code"}

# O identificador do exemplo do 01b §1.
REQUEST_ID = "7b0e1f6c-ativacao-ctr-42"


class TestPartyVerification:
    def test_post_party_verification_pending_aprovada_fica_active(self):
        """CU-P5b: a parte que ficou pending é aprovada pela repescagem.

        O final 98 é o bureau instável (scenario bureau-instavel): a 1ª
        chamada, a do POST /parties, falha e a parte nasce pending; a 2ª, a
        da repescagem, aprova. O reset vem primeiro porque o scenario é
        global ao mock: sem ele, a 1ª chamada já poderia aprovar.
        """
        BureauMock.reset_scenarios()

        document_number = RandomGenerator.generate_cpf_digits(ending="98")
        payload = PayloadGenerator.create_party_payload(document_number=document_number)

        status, response = RequestGenerator.POST_party(payload)
        assert status == 201
        assert response["status"] == "pending"

        party_key = response["party_key"]

        verification_payload = PayloadGenerator.create_party_verification_payload()
        status, response = RequestGenerator.POST_party_verification(party_key, verification_payload)

        assert status == 200
        assert set(response.keys()) == {"party_key", "party_type", "status"}
        assert response["party_key"] == party_key
        assert response["party_type"] == "individual"
        assert response["status"] == "active"

        status, response = RequestGenerator.GET_party(party_key)
        assert status == 200
        assert response["status"] == "active"

        events = DbUtils.party_status_events(party_key)
        transitions = [(e["from_status"], e["to_status"], e["actor"], e["reason"]) for e in events]
        assert transitions == [
            (None, "pending", "erp-alfa", None),
            ("pending", "active", "bureau", "approved"),
        ]

    def test_post_party_verification_evento_carrega_o_x_request_id(self):
        """O evento da repescagem leva o X-Request-ID DA REPESCAGEM (01b §0.1).

        Cada requisição tem o seu identificador: o nascimento fica com o do
        POST /parties, a aprovação com o da repescagem — e é esse mesmo que
        chega ao bureau na 2ª chamada.
        """
        BureauMock.reset_scenarios()

        document_number = RandomGenerator.generate_cpf_digits(ending="98")
        payload = PayloadGenerator.create_party_payload(document_number=document_number)

        status, response, post_request_id = RequestGenerator.POST_party_with_request_id(payload)
        assert status == 201
        assert response["status"] == "pending"

        party_key = response["party_key"]

        verification_payload = PayloadGenerator.create_party_verification_payload()
        status, response, verification_request_id = RequestGenerator.POST_party_verification_with_request_id(
            party_key, verification_payload, REQUEST_ID
        )
        assert status == 200
        assert verification_request_id == REQUEST_ID

        events = DbUtils.party_status_events(party_key)
        assert [e["trace_id"] for e in events] == [post_request_id, REQUEST_ID]

        assert BureauMock.received_request_ids(document_number) == [post_request_id, REQUEST_ID]

    def test_post_party_verification_bureau_fora_do_ar_continua_pending(self):
        """O bureau ainda não responde (final 99): 200, e a parte continua pending.

        Não é erro (G §5, "inclusive se continuou pending"): a repescagem
        tentou, o bureau foi chamado de novo, e nada mudou — nem evento.
        """
        document_number = RandomGenerator.generate_cpf_digits(ending="99")
        payload = PayloadGenerator.create_party_payload(document_number=document_number)

        status, response = RequestGenerator.POST_party(payload)
        assert status == 201
        assert response["status"] == "pending"

        party_key = response["party_key"]

        verification_payload = PayloadGenerator.create_party_verification_payload()
        status, response = RequestGenerator.POST_party_verification(party_key, verification_payload)
        assert status == 200
        assert response["status"] == "pending"

        status, response = RequestGenerator.GET_party(party_key)
        assert status == 200
        assert response["status"] == "pending"

        events = DbUtils.party_status_events(party_key)
        transitions = [(e["from_status"], e["to_status"], e["actor"], e["reason"]) for e in events]
        assert transitions == [(None, "pending", "erp-alfa", None)]

        assert len(BureauMock.received_request_ids(document_number)) == 2

    @pytest.mark.parametrize(
        "field, value",
        [
            ("actor", None),
            ("actor", ""),
            ("actor", "null"),
            ("actor", "a" * 256),
            ("campo_que_nao_existe", 1),
            (None, None),
        ],
        ids=[
            "sem_actor",
            "actor_vazio",
            "actor_nulo",
            "actor_com_256",
            "campo_desconhecido",
            "corpo_ausente",
        ],
    )
    def test_post_party_verification_corpo_fora_do_schema_devolve_400(self, field, value):
        """O schema recusa antes de o controller existir (spec 06, RN-01).

        A parte é a plataforma semeada, que está active: com corpo válido a
        resposta seria outra (409), então o único motivo do 400 é a forma.
        `field` None quer dizer "sem corpo nenhum"; `value` None, "campo
        ausente"; "null", o campo presente com null.
        """
        verification_payload = PayloadGenerator.create_party_verification_payload()

        if field is None:
            verification_payload = None
        elif value is None:
            del verification_payload[field]
        elif value == "null":
            verification_payload[field] = None
        else:
            verification_payload[field] = value

        status, response = RequestGenerator.POST_party_verification(PLATFORM_PARTY_KEY, verification_payload)

        assert status == 400, f"o corpo {verification_payload!r} foi aceito"
        assert response["code"] == "QIT000001"

    def test_post_party_verification_nao_segura_transacao_durante_o_bureau(self):
        """Nenhuma transação de banco aberta enquanto a repescagem espera o bureau.

        A leitura que confere o estado abre uma transação (a sessão tem
        autobegin); ela tem de fechar ANTES da chamada. A repescagem (final
        99, o bureau não responde) roda numa thread, e esta aqui olha o
        pg_stat_activity a cada 100 ms até ela voltar. O tempo mínimo prova
        que a espera aconteceu de verdade.
        """
        document_number = RandomGenerator.generate_cpf_digits(ending="99")
        payload = PayloadGenerator.create_party_payload(document_number=document_number)

        status, response = RequestGenerator.POST_party(payload)
        assert status == 201

        party_key = response["party_key"]
        verification_payload = PayloadGenerator.create_party_verification_payload()
        results = []

        thread = threading.Thread(
            target=lambda: results.append(RequestGenerator.POST_party_verification(party_key, verification_payload))
        )

        started_at = time.monotonic()
        thread.start()

        max_idle_in_transaction = 0
        while thread.is_alive():
            max_idle_in_transaction = max(max_idle_in_transaction, DbUtils.count_idle_in_transaction())
            time.sleep(0.1)

        thread.join()
        elapsed = time.monotonic() - started_at

        status, response = results[0]
        assert status == 200
        assert response["status"] == "pending"
        assert elapsed >= 0.9
        assert max_idle_in_transaction == 0

    @pytest.mark.parametrize("ending", ["00", None, "plataforma"], ids=["rejected", "active", "plataforma"])
    def test_post_party_verification_parte_nao_pending_devolve_409(self, ending):
        """Só pending é verificável (guia §5): rejected é terminal, e active não volta.

        A recusa vem antes do bureau: o número de pedidos que ele recebeu com
        o documento da parte não muda, e a trilha também não. A plataforma é
        a parte semeada (active desde o database.sql).
        """
        if ending == "plataforma":
            party_key = PLATFORM_PARTY_KEY
            document_number = PLATFORM_DOCUMENT_NUMBER
        else:
            document_number = RandomGenerator.generate_cpf_digits(ending=ending)
            payload = PayloadGenerator.create_party_payload(document_number=document_number)

            status, response = RequestGenerator.POST_party(payload)
            assert status == 201
            party_key = response["party_key"]

        status, party_before = RequestGenerator.GET_party(party_key)
        assert status == 200
        assert party_before["status"] in {"active", "rejected"}

        events_before = DbUtils.party_status_events(party_key)
        bureau_requests_before = len(BureauMock.received_request_ids(document_number))

        verification_payload = PayloadGenerator.create_party_verification_payload()
        status, response = RequestGenerator.POST_party_verification(party_key, verification_payload)

        assert status == 409
        assert set(response.keys()) == ERROR_FIELDS
        assert response["code"] == "QIT002004"
        assert party_key in response["description"]

        status, party_after = RequestGenerator.GET_party(party_key)
        assert party_after["status"] == party_before["status"]
        assert DbUtils.party_status_events(party_key) == events_before
        assert len(BureauMock.received_request_ids(document_number)) == bureau_requests_before

    def test_post_party_verification_parte_inexistente_devolve_404(self):
        verification_payload = PayloadGenerator.create_party_verification_payload()

        status, response = RequestGenerator.POST_party_verification(NOT_FOUND_PARTY_KEY, verification_payload)

        assert status == 404
        assert set(response.keys()) == ERROR_FIELDS
        assert response["code"] == "QIT002001"
        assert NOT_FOUND_PARTY_KEY in response["description"]

    def test_post_party_verification_pending_recusada_fica_rejected(self):
        """A repescagem também recusa: pending → rejected, e rejected é terminal.

        O final 97 é o bureau instável que recusa (scenario
        bureau-instavel-recusa, spec 06 P1): a 1ª chamada, a do POST
        /parties, falha; a da repescagem devolve rejected. Uma segunda
        repescagem já encontra a parte fora de pending.
        """
        BureauMock.reset_scenarios()

        document_number = RandomGenerator.generate_cpf_digits(ending="97")
        payload = PayloadGenerator.create_party_payload(document_number=document_number)

        status, response = RequestGenerator.POST_party(payload)
        assert status == 201
        assert response["status"] == "pending"

        party_key = response["party_key"]

        verification_payload = PayloadGenerator.create_party_verification_payload()
        status, response = RequestGenerator.POST_party_verification(party_key, verification_payload)

        assert status == 200
        assert response["party_type"] == "individual"
        assert response["status"] == "rejected"

        status, response = RequestGenerator.GET_party(party_key)
        assert status == 200
        assert response["status"] == "rejected"

        events = DbUtils.party_status_events(party_key)
        transitions = [(e["from_status"], e["to_status"], e["actor"], e["reason"]) for e in events]
        assert transitions == [
            (None, "pending", "erp-alfa", None),
            ("pending", "rejected", "bureau", "rejected"),
        ]

        status, response = RequestGenerator.POST_party_verification(party_key, verification_payload)
        assert status == 409
        assert response["code"] == "QIT002004"
