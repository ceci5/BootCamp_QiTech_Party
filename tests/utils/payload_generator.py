from uuid import uuid4

from tests.utils.random_generator import RandomGenerator


class PayloadGenerator:
    @staticmethod
    def create_sample_entity_payload(
        hello: str = None,
        name: str = None,
        email: str = None,
        document_number: str = None,
        birthdate: str = None,
    ) -> dict:
        """Um cadastro valido, com qualquer campo trocado a pedido.

        Sem argumento nenhum o payload sai aleatorio no que precisa ser
        unico (e-mail e CPF), pra que dois cadastros seguidos nao batam
        na regra de duplicidade. Quem testa FILTRO precisa do contrario
        disso: um valor conhecido, pra poder procurar por ele depois.
        """
        if hello is None:
            hello = "world"

        if name is None:
            name = "Maria da Silva"

        if email is None:
            email = f"maria.silva.{uuid4()}@exemplo.com.br"

        if document_number is None:
            document_number = RandomGenerator.generate_cpf()

        if birthdate is None:
            birthdate = "1990-05-17"

        payload = {
            "hello": hello,
            "name": name,
            "email": email,
            "document_number": document_number,
            "birthdate": birthdate,
        }
        return payload

    @staticmethod
    def create_new_status_payload(new_status: str = None) -> dict:
        payload = {"status": new_status}
        return payload

    @staticmethod
    def create_party_payload(
        name: str = None,
        document_number: str = None,
        pix_key: str = None,
        actor: str = None,
    ) -> dict:
        """Um cadastro de parte valido (spec 03 §8), com qualquer campo trocado.

        Os valores padrao sao os dos documentos (guia §5, 01b §1). O
        documento e sorteado, sem final reservado do bureau: a UNIQUE nao
        deixa repetir um documento fixo entre execucoes. Para mandar sem
        `pix_key`, o teste apaga a chave do dicionario.
        """
        if name is None:
            name = "Ana Souza"

        if document_number is None:
            document_number = RandomGenerator.generate_cpf_digits()

        if pix_key is None:
            pix_key = "ana.locadora@example.com"

        if actor is None:
            actor = "erp-alfa"

        payload = {
            "name": name,
            "document_number": document_number,
            "pix_key": pix_key,
            "actor": actor,
        }
        return payload

    @staticmethod
    def create_client_payload(
        party_key: str,
        platform_fee_percentage: str = None,
        actor: str = None,
    ) -> dict:
        """Um pedido de cliente valido (spec 04 §8), com os valores do guia §5.

        O percentual vai como string, nunca numero (01b §0.3).
        """
        if platform_fee_percentage is None:
            platform_fee_percentage = "1.0000"

        if actor is None:
            actor = "comercial"

        payload = {
            "party_key": party_key,
            "platform_fee_percentage": platform_fee_percentage,
            "actor": actor,
        }
        return payload

    @staticmethod
    def create_party_verification_payload(actor: str = None) -> dict:
        """Um pedido de repescagem valido (spec 06 §8): so o `actor` do guia §5."""
        if actor is None:
            actor = "erp-alfa"

        payload = {"actor": actor}
        return payload
