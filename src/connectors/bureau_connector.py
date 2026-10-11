from typing import Optional

from requests.exceptions import RequestException

from connectors.rest_connector import RestConnector
from constants import BUREAU_API_INTERNAL_TOKEN, BUREAU_API_TIMEOUT, BUREAU_API_URL
from utils.request_context import REQUEST_ID_HEADER, get_request_id


class BureauConnector(RestConnector):
    """Fala com o bureau que verifica CPF e CNPJ (01b §6).

    Acréscimo à base, com as quatro linhas no guia §14. Por que ele faz o
    que o BankSlipConnector não faz:

      • CAPTURA a falha de rede aqui dentro. O RestConnector deixa o
        `requests` levantar, e o controller não pode tratar exceção do
        `requests` (a regra é: `requests` só em connectors/). Para quem
        chama, bureau fora do ar é uma RESPOSTA — "não sei" —, não um erro:
        a parte fica pending e a repescagem resolve depois;

      • manda o X-Request-ID da requisição em andamento, para que o mesmo
        identificador apareça na resposta, na trilha de estado e no bureau
        (01b §0.1).

    O que ele NÃO faz: não repete a chamada, e não muda o RestConnector.
    """

    APPROVED = "approved"
    REJECTED = "rejected"

    def __init__(self) -> None:
        super().__init__(
            class_name=__name__,
            base_url=BUREAU_API_URL,
            timeout=BUREAU_API_TIMEOUT,
            internal_token=BUREAU_API_INTERNAL_TOKEN,
        )

    def verify(self, document_number: str) -> Optional[str]:
        """Devolve "approved", "rejected", ou None se o bureau não respondeu.

        "Não respondeu" inclui timeout, conexão recusada, status que não é
        200 e corpo fora do formato. Nenhuma linha de log leva o documento
        (D0008).
        """
        payload = {"document_number": document_number}
        headers = {REQUEST_ID_HEADER: get_request_id()}

        try:
            response = self.send(endpoint="/verifications", method="POST", payload=payload, headers=headers)
        except RequestException as error:
            self.logger.error(f"Bureau sem resposta: {type(error).__name__}")
            return None

        result = None
        if response.status == 200 and isinstance(response.json, dict):
            result = response.json.get("result")

        if result not in (self.APPROVED, self.REJECTED):
            self.logger.error(f"Bureau respondeu fora do contrato: HTTP {response.status}")
            return None

        return result
