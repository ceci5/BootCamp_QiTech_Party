import threading

from tests.utils import DbUtils, PayloadGenerator, RequestGenerator


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
