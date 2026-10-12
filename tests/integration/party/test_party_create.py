import threading
import time

import pytest

from tests.utils import BureauMock, DbUtils, PayloadGenerator, RandomGenerator, RequestGenerator


ERROR_FIELDS = {"title", "description", "translation", "code"}


class TestPartyCreate:
    def test_post_parties_pf_aprovada_fica_active(self):
        """CU-P1: a pessoa física nasce pending e o bureau a aprova na hora.

        O 201 já traz o estado DEPOIS do bureau, e a trilha conta as duas
        transições: o nascimento (sem estado de origem, com o actor de quem
        pediu) e a aprovação (com o bureau como actor e o desfecho como
        reason).
        """
        payload = PayloadGenerator.create_party_payload()

        status, response = RequestGenerator.POST_party(payload)
        assert status == 201
        assert set(response.keys()) == {"party_key", "party_type", "status"}
        assert response["party_type"] == "individual"
        assert response["status"] == "active"

        party_key = response["party_key"]

        status, response = RequestGenerator.GET_party(party_key)
        assert status == 200
        assert response["status"] == "active"

        events = DbUtils.party_status_events(party_key)
        transitions = [(e["from_status"], e["to_status"], e["actor"], e["reason"]) for e in events]
        assert transitions == [
            (None, "pending", "erp-alfa", None),
            ("pending", "active", "bureau", "approved"),
        ]

    def test_post_parties_documento_repetido_devolve_409(self):
        """CU-P3: o mesmo documento não vira duas partes.

        Quem recusa é a UNIQUE do banco, não um SELECT antes do INSERT: é a
        única forma que segura também duas requisições ao mesmo tempo
        (test_party_concurrency.py).
        """
        primeira = PayloadGenerator.create_party_payload()
        status, _response = RequestGenerator.POST_party(primeira)
        assert status == 201

        segunda = PayloadGenerator.create_party_payload(
            name="Imobiliária Alfa", document_number=primeira["document_number"]
        )
        status, response = RequestGenerator.POST_party(segunda)

        assert status == 409
        assert set(response.keys()) == ERROR_FIELDS
        assert response["code"] == "QIT002003"
        assert DbUtils.count_parties_by_document(primeira["document_number"]) == 1

    @pytest.mark.parametrize(
        "document_number",
        [RandomGenerator.generate_invalid_cpf_digits(), RandomGenerator.generate_invalid_cnpj_digits()],
        ids=["cpf", "cnpj"],
    )
    def test_post_parties_digitos_invalidos_devolve_422(self, document_number):
        """CU-P4: só dígitos, tamanho certo, e mesmo assim não existe.

        O schema cobra o formato; os dígitos verificadores são uma conta
        sobre os outros dígitos, e quem a faz é o controller. Formato certo
        e valor impossível é 422, não 400 — e a recusa vem antes de
        qualquer escrita.
        """
        payload = PayloadGenerator.create_party_payload(document_number=document_number)

        status, response = RequestGenerator.POST_party(payload)

        assert status == 422
        assert response["code"] == "QIT002002"
        assert DbUtils.count_parties_by_document(document_number) == 0

    @pytest.mark.parametrize(
        "field, value",
        [
            ("actor", None),
            ("actor", ""),
            ("name", None),
            ("document_number", "123.456.789-09"),
            ("document_number", "10 digitos"),
            ("document_number", "١٢٣٤٥٦٧٨٩٠٩"),
            ("pix_key", "null"),
            ("pix_key", "isto-nao-e-um-email"),
            ("campo_que_nao_existe", 1),
        ],
        ids=[
            "sem_actor",
            "actor_vazio",
            "sem_name",
            "documento_com_mascara",
            "documento_com_10_digitos",
            "documento_com_digitos_unicode",
            "pix_key_nula",
            "pix_key_fora_do_padrao",
            "campo_desconhecido",
        ],
    )
    def test_post_parties_corpo_fora_do_schema_devolve_400(self, field, value):
        """O schema recusa antes de o controller existir (D0008, item 3).

        `None` quer dizer "campo ausente". O documento com dígitos
        arábico-índicos é o CPF do guia §5 escrito com outros dígitos: o
        `\\d` aceitaria, o `[0-9]` do schema não (spec 03, P1).
        """
        payload = PayloadGenerator.create_party_payload()

        if value is None:
            del payload[field]
        elif value == "10 digitos":
            payload[field] = payload["document_number"][:-1]
        elif value == "null":
            payload[field] = None
        else:
            payload[field] = value

        status, response = RequestGenerator.POST_party(payload)

        assert status == 400, f"o campo '{field}' aceitou o valor {value!r}"
        assert response["code"] == "QIT000001"

    @pytest.mark.parametrize(
        "field, value",
        [
            ("document_number", RandomGenerator.generate_cpf_digits() + "\n"),
            ("document_number", RandomGenerator.generate_cnpj_digits() + "\n"),
            ("pix_key", "a@b\n"),
        ],
        ids=["documento_cpf", "documento_cnpj", "pix_key"],
    )
    def test_post_parties_quebra_de_linha_no_fim_devolve_400(self, field, value):
        """Um `\\n` no fim não passa no schema (PAR-01).

        O `$` do `re` do Python casa antes de um `\\n` final: sem o
        `(?!\\n)`, o CNPJ com `\\n` virava 500, o CPF 422, e a chave pix
        era gravada com a quebra de linha. Nada pode chegar ao banco.
        """
        payload = PayloadGenerator.create_party_payload()
        payload[field] = value

        status, response = RequestGenerator.POST_party(payload)

        assert status == 400, f"o campo '{field}' aceitou o valor {value!r}"
        assert response["code"] == "QIT000001"
        for document_number in {payload["document_number"], payload["document_number"].rstrip("\n")}:
            assert DbUtils.count_parties_by_document(document_number) == 0

    def test_post_parties_pj_aprovada_fica_active(self):
        """CU-P2: a pessoa jurídica segue o mesmo caminho, com o tipo organization."""
        payload = PayloadGenerator.create_party_payload(
            name="Imobiliária Alfa",
            document_number=RandomGenerator.generate_cnpj_digits(),
            pix_key="financeiro@alfa.example",
        )

        status, response = RequestGenerator.POST_party(payload)
        assert status == 201
        assert response["party_type"] == "organization"
        assert response["status"] == "active"

        events = DbUtils.party_status_events(response["party_key"])
        transitions = [(e["from_status"], e["to_status"], e["actor"], e["reason"]) for e in events]
        assert transitions == [
            (None, "pending", "erp-alfa", None),
            ("pending", "active", "bureau", "approved"),
        ]

    def test_post_parties_bureau_fora_do_ar_fica_pending(self):
        """CU-P5a: o bureau não respondeu, e a parte fica pending — sem erro.

        O final 99 faz o mock atrasar 2000 ms, mais que o timeout. O
        cadastro já estava salvo antes da chamada; o que falta é só a
        verificação, que a repescagem (fatia 06) faz depois.
        """
        document_number = RandomGenerator.generate_cpf_digits(ending="99")
        payload = PayloadGenerator.create_party_payload(document_number=document_number)

        status, response = RequestGenerator.POST_party(payload)
        assert status == 201
        assert response["status"] == "pending"

        party_key = response["party_key"]

        assert len(BureauMock.received_request_ids(document_number)) == 1

        status, response = RequestGenerator.GET_party(party_key)
        assert status == 200
        assert response["status"] == "pending"

        events = DbUtils.party_status_events(party_key)
        assert [(e["from_status"], e["to_status"]) for e in events] == [(None, "pending")]

    def test_post_parties_bureau_recusa_fica_rejected(self):
        """O bureau recusou (final 00): a parte existe, e nasce recusada.

        Não é erro de quem pediu — é 201, com o desfecho no status.
        """
        document_number = RandomGenerator.generate_cpf_digits(ending="00")
        payload = PayloadGenerator.create_party_payload(document_number=document_number)

        status, response = RequestGenerator.POST_party(payload)
        assert status == 201
        assert response["status"] == "rejected"

        events = DbUtils.party_status_events(response["party_key"])
        transitions = [(e["from_status"], e["to_status"], e["actor"], e["reason"]) for e in events]
        assert transitions == [
            (None, "pending", "erp-alfa", None),
            ("pending", "rejected", "bureau", "rejected"),
        ]

    def test_post_parties_nao_segura_transacao_durante_o_bureau(self):
        """Nenhuma transação de banco aberta enquanto a API espera o bureau.

        O POST (final 99, o bureau não responde) roda numa thread; esta
        aqui olha o pg_stat_activity a cada 100 ms até ele voltar. Uma
        conexão parada no meio de uma transação durante a espera inteira é
        o sintoma de alguém ter lido um atributo do model depois do commit
        (o expire_on_commit reabre a transação). O tempo mínimo prova que a
        espera aconteceu de verdade.
        """
        document_number = RandomGenerator.generate_cpf_digits(ending="99")
        payload = PayloadGenerator.create_party_payload(document_number=document_number)
        results = []

        thread = threading.Thread(target=lambda: results.append(RequestGenerator.POST_party(payload)))

        started_at = time.monotonic()
        thread.start()

        max_idle_in_transaction = 0
        while thread.is_alive():
            max_idle_in_transaction = max(max_idle_in_transaction, DbUtils.count_idle_in_transaction())
            time.sleep(0.1)

        thread.join()
        elapsed = time.monotonic() - started_at

        assert results[0][0] == 201
        assert elapsed >= 0.9
        assert max_idle_in_transaction == 0
