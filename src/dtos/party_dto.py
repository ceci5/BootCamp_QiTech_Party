from models import Party
from utils.document_number import CPF_LENGTH


class PartyDTO:
    """Traduz a parte no JSON que a API devolve.

    É aqui, e só aqui, que se decide o que sai. O `GET /parties/{key}` é
    lido pelo Contrato e pelo Ledger (01b §1): os campos são exatamente os
    do contrato, e nome e documento NUNCA saem (D0008). O documento é
    usado só para dizer o tipo da parte — e o tipo sai, o número não.
    """

    @staticmethod
    def obj_to_dict(party: Party) -> dict:
        dto = dict()
        dto["party_key"] = party.party_key
        dto["party_type"] = PartyDTO.party_type(party)
        dto["status"] = party.status.enumerator
        dto["pix_key"] = party.pix_key
        # Quem diz se a parte é cliente da plataforma é a fatia 04 (tabela
        # client). Até lá, nenhuma parte é.
        dto["client_key"] = None

        return dto

    @staticmethod
    def obj_to_creation_dict(party: Party) -> dict:
        """O que o POST /parties devolve: a chave, o tipo e o estado (guia §5)."""
        dto = dict()
        dto["party_key"] = party.party_key
        dto["party_type"] = PartyDTO.party_type(party)
        dto["status"] = party.status.enumerator

        return dto

    @staticmethod
    def party_type(party: Party) -> str:
        """11 dígitos é pessoa física; 14, jurídica (guia §5)."""
        if len(party.document_number) == CPF_LENGTH:
            return Party.INDIVIDUAL

        return Party.ORGANIZATION
