import random


class RandomGenerator:
    @staticmethod
    def generate_cpf():
        cpf = [random.randrange(10) for _ in range(9)]
        for _ in range(2):
            value = sum([(len(cpf) + 1 - i) * v for i, v in enumerate(cpf)]) % 11
            cpf.append(11 - value if value > 1 else 0)
        cpf_number = "".join(str(x) for x in cpf)
        cpf_number = f"{cpf_number[0:3]}.{cpf_number[3:6]}.{cpf_number[6:9]}-{cpf_number[9:11]}"
        return cpf_number

    @staticmethod
    def generate_cnpj():
        cnpj = [random.randrange(10) for _ in range(8)] + [0, 0, 0, 1]

        for _ in range(2):
            value = sum(v * (i % 8 + 2) for i, v in enumerate(reversed(cnpj)))
            digit = 11 - value % 11
            cnpj.append(digit if digit < 10 else 0)

        cnpj_number = "".join(str(x) for x in cnpj)

        cnpj_number = (
            f"{cnpj_number[0:2]}.{cnpj_number[2:5]}.{cnpj_number[5:8]}/{cnpj_number[8:12]}-{cnpj_number[12:14]}"
        )

        return cnpj_number

    # ────────────────────────────────────────────────────────────────
    # Documentos SÓ DÍGITOS, para a party-api (spec 03, sumário L16)
    # ────────────────────────────────────────────────────────────────
    # O bureau mockado decide pelo final do documento: 00 recusa, 99 fica
    # fora do ar, 98 falha uma vez e aprova, 97 falha uma vez e recusa
    # (spec 06). Um sorteio comum que caísse num desses
    # finais mudaria o desfecho do teste ~1 vez em 100 — por isso, sem
    # `ending`, eles são sorteados de novo. Com `ending`, o sorteio repete
    # até o documento terminar exatamente nele.
    RESERVED_ENDINGS = ("00", "97", "98", "99")

    # A parte da plataforma, semeada no database.sql: um POST com este CNPJ
    # bateria na UNIQUE e daria 409 por acaso.
    PLATFORM_CNPJ = "11222333000181"

    @staticmethod
    def _cpf_digits() -> str:
        cpf = [random.randrange(10) for _ in range(9)]
        for _ in range(2):
            value = sum([(len(cpf) + 1 - i) * v for i, v in enumerate(cpf)]) % 11
            cpf.append(11 - value if value > 1 else 0)
        return "".join(str(x) for x in cpf)

    @staticmethod
    def _cnpj_digits() -> str:
        cnpj = [random.randrange(10) for _ in range(8)] + [0, 0, 0, 1]

        for _ in range(2):
            value = sum(v * (i % 8 + 2) for i, v in enumerate(reversed(cnpj)))
            digit = 11 - value % 11
            cnpj.append(digit if digit < 10 else 0)

        return "".join(str(x) for x in cnpj)

    @staticmethod
    def _draw(draw_function, ending: str = None, excluded: tuple = ()) -> str:
        while True:
            document_number = draw_function()

            if document_number in excluded:
                continue

            if ending is None and document_number[-2:] not in RandomGenerator.RESERVED_ENDINGS:
                return document_number

            if ending is not None and document_number.endswith(ending):
                return document_number

    @staticmethod
    def generate_cpf_digits(ending: str = None) -> str:
        return RandomGenerator._draw(RandomGenerator._cpf_digits, ending)

    @staticmethod
    def generate_cnpj_digits(ending: str = None) -> str:
        return RandomGenerator._draw(
            RandomGenerator._cnpj_digits, ending, excluded=(RandomGenerator.PLATFORM_CNPJ,)
        )

    @staticmethod
    def _break_last_digit(document_number: str) -> str:
        """Troca o último dígito verificador: o número continua com a cara
        certa (só dígitos, tamanho certo) e deixa de existir."""
        last_digit = (int(document_number[-1]) + 1) % 10
        return f"{document_number[:-1]}{last_digit}"

    @staticmethod
    def generate_invalid_cpf_digits() -> str:
        return RandomGenerator._break_last_digit(RandomGenerator.generate_cpf_digits())

    @staticmethod
    def generate_invalid_cnpj_digits() -> str:
        return RandomGenerator._break_last_digit(RandomGenerator.generate_cnpj_digits())
