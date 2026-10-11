from errors import QIException


class NotFoundSampleEntity(QIException):
    code = "QIT001001"

    def __init__(self, sample_entity_key) -> None:
        title = "Entity not Found"
        http_status = 404
        description = f"Entity with key {sample_entity_key} was not found."
        translation = f"A entidade com chave {sample_entity_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class SampleEntityFinalStatus(QIException):
    code = "QIT001002"

    def __init__(self, old_status, new_status) -> None:
        title = "Entity cannot change status"
        http_status = 409
        description = f"Entity with status {old_status} cannot update to {new_status}."
        translation = "Essa entidade não pode ser atualizada."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumentNumber(QIException):
    """O CPF tem o formato certo e não existe.

    422, e não 400, de propósito: 400 quer dizer "não consegui ler o seu
    pedido". Aqui a API leu, entendeu, e o valor é que não pode existir —
    os dois últimos dígitos não batem com a conta. A diferença está
    explicada em src/utils/document_number.py.
    """

    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF."
        translation = "O CPF informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):
    """Já existe um cadastro com este CPF.

    409 Conflict: o pedido está correto em si, e o que impede é o que já
    está no banco. É a mesma família do SampleEntityFinalStatus aqui em
    cima — conflito com o que já existe, não erro de quem pediu.
    """

    code = "QIT001004"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = f"There is already an entity with the document number {document_number}."
        translation = "Já existe um cadastro com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedEmail(QIException):
    code = "QIT001005"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already an entity with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class UnderageSampleEntity(QIException):
    code = "QIT001006"

    def __init__(self, age, minimum_age) -> None:
        title = "Entity is underage"
        http_status = 422
        description = f"The entity is {age} years old, and the minimum is {minimum_age}."
        translation = f"É preciso ter pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBirthdate(QIException):
    """A data tem o formato certo e não existe no calendário.

    Existe porque o `pattern` do schema sabe contar dígitos, não dias:
    "2025-02-30" e "9999-99-99" passam pelo regex e morrem no
    `date.fromisoformat`. Sem esta classe, esse ValueError virava 500 —
    a API culpando a si mesma por um erro de quem chamou.
    """

    code = "QIT001007"

    def __init__(self, birthdate) -> None:
        title = "Invalid Birthdate"
        http_status = 422
        description = f"The birthdate {birthdate} is not a real date."
        translation = "A data de nascimento informada não existe."
        super().__init__(title, self.code, http_status, description, translation)


class PartyNotFound(QIException):
    """A parte não existe. É o 404 que o Contrato e o Ledger traduzem
    (01b §1), por isso o texto é o mesmo do mock (spec 02 §3.5).

    A descrição leva só a chave, nunca nome nem documento (D0008).
    """

    code = "QIT002001"

    def __init__(self, party_key) -> None:
        title = "Party not found"
        http_status = 404
        description = f"Party with key {party_key} was not found."
        translation = f"A parte com chave {party_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidPartyDocument(QIException):
    """Só dígitos, tamanho certo, e os dígitos verificadores não batem.

    422, como o InvalidDocumentNumber da sample_entity: a API leu e o valor
    é que não pode existir. A descrição não repete o documento (D0008).
    """

    code = "QIT002002"

    def __init__(self) -> None:
        title = "Invalid party document"
        http_status = 422
        description = "The document number is not a valid CPF or CNPJ."
        translation = "O documento informado não é um CPF nem um CNPJ válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedPartyDocument(QIException):
    """Já existe uma parte com este documento.

    409: o pedido está certo em si, e o que impede é o que já está no
    banco. Quem decide é a UNIQUE da tabela, não uma consulta antes do
    INSERT (sumário L6). A descrição não repete o documento (D0008).
    """

    code = "QIT002003"

    def __init__(self) -> None:
        title = "Party document already registered"
        http_status = 409
        description = "There is already a party with this document number."
        translation = "Já existe uma parte cadastrada com este documento."
        super().__init__(title, self.code, http_status, description, translation)


class ClientNotFound(QIException):
    """O cliente não existe. É o 404 que o Contrato traduz (01b §2), por
    isso o texto é o mesmo do mock (clients-c404c404-404.json).

    A descrição leva só a chave, nunca nome nem documento (D0008).
    """

    code = "QIT002005"

    def __init__(self, client_key) -> None:
        title = "Client not found"
        http_status = 404
        description = f"Client with key {client_key} was not found."
        translation = f"O cliente com chave {client_key} não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class ClientMustBeOrganization(QIException):
    """Só pessoa jurídica vira cliente da plataforma (guia §5).

    422: a API leu o pedido, e uma pessoa física não pode ser cliente —
    nem agora, nem depois, porque o tipo da parte não muda. A descrição
    leva só a chave (D0008).
    """

    code = "QIT002006"

    def __init__(self, party_key) -> None:
        title = "Client must be an organization"
        http_status = 422
        description = f"Party with key {party_key} is not an organization."
        translation = f"A parte com chave {party_key} não é pessoa jurídica."
        super().__init__(title, self.code, http_status, description, translation)


class PartyNotActive(QIException):
    """A parte existe, é jurídica, e ainda não está ativa (pending) ou nunca
    vai estar (rejected).

    409: conflito com o estado em que a parte está. A descrição leva a
    chave e o estado, nunca nome nem documento (D0008).
    """

    code = "QIT002008"

    def __init__(self, party_key, status) -> None:
        title = "Party is not active"
        http_status = 409
        description = f"Party with key {party_key} is {status}, not active."
        translation = f"A parte com chave {party_key} não está ativa."
        super().__init__(title, self.code, http_status, description, translation)


class PartyAlreadyClient(QIException):
    """A parte já é cliente da plataforma: uma por parte (RFC).

    409: o pedido está certo em si, e o que impede é o que já está no
    banco. Quem decide é a UNIQUE(party_id) da tabela client, não uma
    consulta antes do INSERT (sumário L6). A descrição leva só a chave.
    """

    code = "QIT002007"

    def __init__(self, party_key) -> None:
        title = "Party is already a client"
        http_status = 409
        description = f"Party with key {party_key} is already a client."
        translation = f"A parte com chave {party_key} já é cliente."
        super().__init__(title, self.code, http_status, description, translation)


class PartyNotVerifiable(QIException):
    """A repescagem só vale para a parte pending (guia §5).

    409: conflito com o estado em que a parte está. rejected é terminal
    (D0010) e active não volta (06 §2.1): perguntar de novo ao bureau não
    mudaria nada. A descrição leva a chave e o estado, nunca nome nem
    documento (D0008).
    """

    code = "QIT002004"

    def __init__(self, party_key, status) -> None:
        title = "Party cannot be verified"
        http_status = 409
        description = f"Party with key {party_key} is {status}, not pending."
        translation = f"A parte com chave {party_key} não está pendente de verificação."
        super().__init__(title, self.code, http_status, description, translation)
