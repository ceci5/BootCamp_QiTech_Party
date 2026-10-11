from typing import List

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
        # A chave do cliente da plataforma que esta parte é, ou null se não
        # for (01b §1). No máximo um cliente por parte (tabela client).
        dto["client_key"] = None
        if party.client is not None:
            dto["client_key"] = party.client.client_key

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
    def obj_to_simplified_dict(party: Party) -> dict:
        """O item da busca por documento: só a chave e o estado (guia §5).

        Quem busca já tem o documento; o que lhe falta é a chave. Nada
        mais sai (D0008).
        """
        dto = dict()
        dto["party_key"] = party.party_key
        dto["status"] = party.status.enumerator

        return dto

    @staticmethod
    def list_obj_to_list_dict(parties_list: List[Party]) -> List[dict]:
        parties_dict_list = []

        for party in parties_list:
            parties_dict_list.append(PartyDTO.obj_to_simplified_dict(party))

        return parties_dict_list

    @staticmethod
    def party_type(party: Party) -> str:
        """11 dígitos é pessoa física; 14, jurídica (guia §5)."""
        if len(party.document_number) == CPF_LENGTH:
            return Party.INDIVIDUAL

        return Party.ORGANIZATION
