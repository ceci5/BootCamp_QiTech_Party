from decimal import Decimal

from models import Client

# Quatro casas decimais, sempre (01b §0.3: "1.0000").
PERCENTAGE_PLACES = Decimal("0.0001")


class ClientDTO:
    """Traduz o cliente no JSON que a API devolve (01b §2).

    O GET /clients/{key} é lido pelo Contrato: os campos são exatamente os
    do contrato, e nome e documento da parte NUNCA saem (D0008). O estado é
    o da parte por trás do cliente — o cliente não tem estado próprio
    (06 §3).
    """

    @staticmethod
    def obj_to_dict(client: Client) -> dict:
        dto = dict()
        dto["client_key"] = client.client_key
        dto["party_key"] = client.party.party_key
        dto["status"] = client.party.status.enumerator
        dto["platform_fee_percentage"] = ClientDTO.percentage_to_str(client.platform_fee_percentage)

        return dto

    @staticmethod
    def percentage_to_str(percentage: Decimal) -> str:
        """O percentual em texto, com quatro casas mesmo que tenha entrado sem elas.

        Lido do banco, o NUMERIC(7,4) já vem com quatro casas. Recém-criado,
        antes do commit, o objeto guarda a escala de quem enviou —
        Decimal("1") vira "1", não "1.0000" (medido, spec 04). O quantize
        faz o 201 sair igual ao GET.
        """
        return str(percentage.quantize(PERCENTAGE_PLACES))
