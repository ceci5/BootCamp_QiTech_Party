import logging
import re
import sys

from constants import APP_ENV, SERVICE_NAME
from utils.request_context import get_request_id


# O "[%(request_id)s]" é o identificador da requisição que gerou a linha
# — quem o preenche é o filtro logo abaixo. Uma linha sai assim:
#
#   2026-09-01 12:00:00 [INFO] bootcamp-api.middlewares.request_logger
#   [8f3c1e42-...] - ENTROU GET /sample_entities
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s [%(request_id)s] - %(message)s"


class RequestIdFilter(logging.Filter):
    """Carimba toda linha de log com o identificador da requisição.

    "Filter" é um nome infeliz do Python: esta classe não descarta nada
    — ela devolve True para tudo. O que ela faz é acrescentar um campo à
    linha antes de a formatação acontecer. É o gancho oficial do módulo
    de log para isso.

    A alternativa seria lembrar de escrever o identificador em cada
    chamada de logger.info do projeto. Uma hora alguém esquece, e é
    justamente na linha que você iria precisar.

    Quando não há requisição em andamento — a API subindo, por
    exemplo — o campo sai como "-", e nada quebra.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


# Um CPF (11 dígitos) ou um CNPJ (14) solto na linha: nem colado a outro
# dígito antes, nem depois. O primeiro grupo é o que some; o segundo, os dois
# últimos dígitos, fica. Com 11 dígitos casa 9 + 2; com 14, o 9 + 2 esbarra
# no dígito seguinte e o regex tenta 12 + 2.
DOCUMENT_NUMBER_PATTERN = re.compile(r"(?<![0-9])([0-9]{9}|[0-9]{12})([0-9]{2})(?![0-9])")


def mask_document_numbers(text: str) -> str:
    """Troca cada dígito escondido por `*`: 12345678909 vira *********09."""
    return DOCUMENT_NUMBER_PATTERN.sub(lambda match: "*" * len(match.group(1)) + match.group(2), text)


class DocumentMaskFilter(logging.Filter):
    """Mascara CPF e CNPJ em toda linha de log (D0008; sumário C3; guia §14).

    O request_logger grava a query string, e a busca por documento
    (GET /parties?document_number=) poria o documento ali em texto puro. Em
    vez de mexer no middleware, este filtro reescreve a linha antes de ela
    sair: a mensagem, os argumentos dela (o log de acesso do uvicorn monta
    a linha a partir de uma tupla de argumentos, e a tupla precisa manter o
    tamanho) e o texto da exceção.

    O `exc_text` é preenchido aqui porque o Formatter só o preencheria
    DEPOIS dos filtros, já sem máscara.

    Como o RequestIdFilter, ele nunca descarta nada: devolve True sempre.
    O preço: qualquer número solto de 11 ou 14 dígitos sai mascarado, seja
    ou não um documento.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_document_numbers(record.msg)

        if isinstance(record.args, tuple):
            record.args = tuple(
                mask_document_numbers(arg) if isinstance(arg, str) else arg for arg in record.args
            )

        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)

        if record.exc_text:
            record.exc_text = mask_document_numbers(record.exc_text)

        return True


def setup_logging() -> None:
    """Liga o log da aplicação. Chamada uma vez, quando a API sobe."""
    level = logging.INFO
    if APP_ENV.upper() in ("LOCAL", "TEST"):
        level = logging.DEBUG

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # O filtro fica no HANDLER, não num logger específico: assim toda
    # linha que passar por aqui ganha o campo, venha ela do nosso código
    # ou de qualquer biblioteca. Se ficasse num logger só, a primeira
    # linha vinda de outro lugar derrubaria a formatação.
    handler.addFilter(RequestIdFilter())
    handler.addFilter(DocumentMaskFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    # O urllib3 fala MUITO em modo debug, e nada disso e nosso: sao
    # detalhes de conexao HTTP das bibliotecas que usamos.
    for biblioteca_falante in ["urllib3"]:
        logging.getLogger(biblioteca_falante).setLevel(logging.CRITICAL)

    # O uvicorn escreve pelos próprios loggers, com handler próprio e sem
    # propagar até a raiz: o filtro do handler acima não os alcança, e a
    # linha de acesso traz a query string inteira (spec 07, P1).
    logging.getLogger("uvicorn.access").addFilter(DocumentMaskFilter())
    logging.getLogger("uvicorn.error").addFilter(DocumentMaskFilter())


def get_logger(class_name: str) -> logging.Logger:
    """Devolve o log com o nome de quem está escrevendo.

    Assim, olhando a linha do log, você sabe de qual arquivo ela veio.
    """
    return logging.getLogger(f"{SERVICE_NAME}.{class_name}")
