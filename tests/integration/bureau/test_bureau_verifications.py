import pytest

from tests.utils import BureauMock


# O timeout com que a suite foi escrita (BUREAU_API_TIMEOUT=1 no .env.example).
TEST_TIMEOUT = 1


class TestBureauVerifications:
    @pytest.mark.parametrize("document_number", ["12345678909", "12345678000195"])
    def test_verifications_documento_comum_aprova(self, document_number):
        status, response = BureauMock.POST_verifications(document_number, timeout=TEST_TIMEOUT)
        assert status == 200
        assert response == {"result": "approved"}

    def test_verifications_mock_carrega_os_cinco_mappings(self):
        assert BureauMock.mappings_total() == 5
