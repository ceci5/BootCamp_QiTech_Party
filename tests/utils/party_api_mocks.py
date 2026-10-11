import json
from pathlib import Path


# A cópia dos mocks do Cadastro (spec 05, sumário L7). A fonte é
# bootcamp-qi-tech-docs/docs/mocks/party-api/mappings/: aqui só se copia,
# nunca se edita.
MAPPINGS_DIR = Path(__file__).resolve().parents[1] / "mocks" / "party-api" / "mappings"

MOCKS_MISSING = (
    "A cópia dos mocks do Cadastro não existe em {dir}.\n"
    "Copie de bootcamp-qi-tech-docs/docs/mocks/party-api/mappings/ (sumário L7)."
)


class PartyApiMocks:
    """Lê os mappings WireMock que o Cadastro publica para os outros dois.

    São os arquivos que o Contrato e o Ledger usam no lugar desta API. O
    test_contrato_01b.py compara cada um com a resposta da API real: se
    os dois concordam, quem testa contra o mock testa contra a verdade
    (00 §1, regra 2). Lê os arquivos direto, sem subir WireMock.
    """

    @staticmethod
    def mappings() -> list:
        """Todos os mappings da cópia, em ordem de nome, com o nome em "_file"."""
        files = sorted(MAPPINGS_DIR.glob("*.json")) if MAPPINGS_DIR.is_dir() else []
        if not files:
            raise RuntimeError(MOCKS_MISSING.format(dir=MAPPINGS_DIR))

        mappings = []
        for file in files:
            mapping = json.loads(file.read_text(encoding="utf-8"))
            mapping["_file"] = file.name
            mappings.append(mapping)

        return mappings

    @staticmethod
    def by_url_path(url_path: str) -> list:
        """Os mappings que casam exatamente este caminho (o teste confere que é um)."""
        return [mapping for mapping in PartyApiMocks.mappings() if mapping["request"].get("urlPath") == url_path]

    @staticmethod
    def by_url_path_pattern(pattern: str) -> list:
        """Os pega-tudo: mappings por expressão de caminho, não por chave."""
        return [
            mapping for mapping in PartyApiMocks.mappings() if mapping["request"].get("urlPathPattern") == pattern
        ]
