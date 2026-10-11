import threading

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator


class TestClientConcurrency:
    def test_post_clients_simultaneos_mesma_parte_um_201_um_409(self):
        """Dois pedidos para tornar a mesma parte cliente, soltos no mesmo instante.

        A Barrier segura as duas threads até as duas estarem prontas e
        solta juntas: sem ela, a segunda costuma chegar depois de a
        primeira já ter terminado, e o teste prova só a repetição em
        série. Um SELECT antes do INSERT deixaria as duas passarem; a
        UNIQUE(party_id) do banco deixa uma.
        """
        party_key = ObjectGenerator.create_organization_party()["party_key"]
        payload = PayloadGenerator.create_client_payload(party_key)
        barrier = threading.Barrier(2)
        results = []

        def post_client():
            barrier.wait()
            results.append(RequestGenerator.POST_client(payload))

        threads = [threading.Thread(target=post_client) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        statuses = sorted(status for status, _response in results)
        assert statuses == [201, 409]

        created_client = [response for status, response in results if status == 201][0]
        conflict_response = [response for status, response in results if status == 409][0]
        assert conflict_response["code"] == "QIT002007"

        status, response = RequestGenerator.GET_party(party_key)
        assert status == 200
        assert response["client_key"] == created_client["client_key"]
