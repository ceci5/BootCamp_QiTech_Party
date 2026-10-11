import threading

from tests.utils import BureauMock, DbUtils, PayloadGenerator, RandomGenerator, RequestGenerator


class TestPartyConcurrency:
    def test_post_parties_simultaneos_mesmo_documento_um_201_um_409(self):
        """Duas requisições com o mesmo documento, soltas no mesmo instante.

        A Barrier segura as duas threads até as duas estarem prontas e
        solta juntas: sem ela, a segunda costuma chegar depois de a
        primeira já ter terminado, e o teste prova só a duplicidade em
        série. Um SELECT antes do INSERT deixaria as duas passarem; a
        UNIQUE do banco deixa uma.
        """
        payload = PayloadGenerator.create_party_payload()
        barrier = threading.Barrier(2)
        results = []

        def post_party():
            barrier.wait()
            results.append(RequestGenerator.POST_party(payload))

        threads = [threading.Thread(target=post_party) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        statuses = sorted(status for status, _response in results)
        assert statuses == [201, 409]

        conflict_response = [response for status, response in results if status == 409][0]
        assert conflict_response["code"] == "QIT002003"

        assert DbUtils.count_parties_by_document(payload["document_number"]) == 1

    def test_post_party_verification_simultaneas_uma_transicao_so(self):
        """Duas repescagens da mesma parte pending, soltas no mesmo instante.

        O final 98 deixa a parte pending (a 1ª chamada ao bureau falha) e faz
        o bureau aprovar todas as seguintes. Conforme a intercalação, as duas
        chegam ao bureau e a segunda a pegar a trava (FOR UPDATE) vê active e
        não grava (sumário L14) — {200, 200} —, ou uma lê depois do commit da
        outra e leva 409 sem chamar o bureau — {200, 409}. Nos dois casos, a
        trilha tem UMA transição de saída de pending.
        """
        BureauMock.reset_scenarios()

        document_number = RandomGenerator.generate_cpf_digits(ending="98")
        payload = PayloadGenerator.create_party_payload(document_number=document_number)

        status, response = RequestGenerator.POST_party(payload)
        assert status == 201
        assert response["status"] == "pending"

        party_key = response["party_key"]
        verification_payload = PayloadGenerator.create_party_verification_payload()
        barrier = threading.Barrier(2)
        results = []

        def post_verification():
            barrier.wait()
            results.append(RequestGenerator.POST_party_verification(party_key, verification_payload))

        threads = [threading.Thread(target=post_verification) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        for status, response in results:
            if status == 200:
                assert response["status"] == "active"
            else:
                assert status == 409
                assert response["code"] == "QIT002004"

        successes = [status for status, _response in results if status == 200]
        assert len(successes) >= 1

        status, response = RequestGenerator.GET_party(party_key)
        assert response["status"] == "active"

        events = DbUtils.party_status_events(party_key)
        transitions = [(e["from_status"], e["to_status"], e["actor"], e["reason"]) for e in events]
        assert transitions == [
            (None, "pending", "erp-alfa", None),
            ("pending", "active", "bureau", "approved"),
        ]

        assert len(BureauMock.received_request_ids(document_number)) == 1 + len(successes)
