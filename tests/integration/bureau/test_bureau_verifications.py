import time

import pytest

from tests.utils import BureauMock


# O timeout com que a suite foi escrita (BUREAU_API_TIMEOUT=1 no .env.example)
# e o padrao do compose sem .env (3). O "fora do ar" atrasa 2000 ms: com o
# primeiro quem chama ve timeout, com o segundo ve 503 (sumario C1).
TEST_TIMEOUT = 1
DEFAULT_TIMEOUT = 3


class TestBureauVerifications:
    @pytest.mark.parametrize("document_number", ["12345678909", "12345678000195"])
    def test_verifications_documento_comum_aprova(self, document_number):
        status, response = BureauMock.POST_verifications(document_number, timeout=TEST_TIMEOUT)
        assert status == 200
        assert response == {"result": "approved"}

    def test_verifications_final_00_recusa(self):
        status, response = BureauMock.POST_verifications("12345678900", timeout=TEST_TIMEOUT)
        assert status == 200
        assert response == {"result": "rejected"}

    def test_verifications_final_99_fora_do_ar(self):
        status, response = BureauMock.POST_verifications("12345678999", timeout=TEST_TIMEOUT)
        assert status is None

        start = time.monotonic()
        status, response = BureauMock.POST_verifications("12345678999", timeout=DEFAULT_TIMEOUT)
        elapsed = time.monotonic() - start
        assert status == 503
        assert response is None
        assert elapsed >= 2

    def test_verifications_final_98_falha_uma_vez_e_aprova(self):
        assert BureauMock.reset_scenarios() == 200

        status, response = BureauMock.POST_verifications("12345678998", timeout=TEST_TIMEOUT)
        assert status is None

        for _ in range(2):
            status, response = BureauMock.POST_verifications("12345678998", timeout=TEST_TIMEOUT)
            assert status == 200
            assert response == {"result": "approved"}

    def test_verifications_final_97_falha_uma_vez_e_recusa(self):
        """O par do 98 para a recusa (spec 06, P1): falha uma vez e depois recusa.

        Scenario proprio (bureau-instavel-recusa), para nao dividir estado
        com o 98; o mesmo reset zera os dois.
        """
        assert BureauMock.reset_scenarios() == 200

        status, response = BureauMock.POST_verifications("12345678997", timeout=TEST_TIMEOUT)
        assert status is None

        for _ in range(2):
            status, response = BureauMock.POST_verifications("12345678997", timeout=TEST_TIMEOUT)
            assert status == 200
            assert response == {"result": "rejected"}

    def test_verifications_mock_carrega_os_sete_mappings(self):
        """Padrao, 00, 99, os dois do 98 e os dois do 97 (spec 02, emenda de 2026-10-11)."""
        assert BureauMock.mappings_total() == 7
