CPF_LENGTH = 11

CHECK_DIGIT_POSITIONS = [9, 10]


def is_valid_cpf(document_number: str) -> bool:
    """Diz se um CPF existe de verdade — não se ele tem a cara certa.

    O schema em src/schemas/post_sample_entity.json já cobrou o formato:
    três pontos, um hífen, onze dígitos. Isto aqui é outra pergunta, e a
    diferença entre as duas é a lição deste arquivo.

    Os dois últimos dígitos de um CPF não são escolhidos: eles são o
    RESULTADO de uma conta feita sobre os nove primeiros. Por isso um
    número pode ter o formato perfeito e não existir — "111.222.333-44"
    passa no schema e não passa aqui.

    É o mesmo motivo pelo qual a resposta dessa recusa é 422 e não 400:
    não é que a API não conseguiu ler o pedido; ela leu, entendeu, e o
    valor não pode existir.

    A conta, para cada um dos dois dígitos: multiplica cada dígito
    anterior por um peso que decresce, soma tudo, tira o resto da divisão
    por 11. Resto menor que 2 vira dígito 0; nos outros casos, o dígito é
    11 menos o resto.
    """
    digits = []
    for character in document_number:
        if character.isdigit():
            digits.append(int(character))

    if len(digits) != CPF_LENGTH:
        return False

    # Um CPF de dígitos todos iguais ("111.111.111-11") passa na conta
    # dos dígitos verificadores e mesmo assim não vale. São onze números
    # conhecidos, e a Receita não emite nenhum deles.
    all_digits_are_equal = True
    for digit in digits:
        if digit != digits[0]:
            all_digits_are_equal = False
            break

    if all_digits_are_equal:
        return False

    for position in CHECK_DIGIT_POSITIONS:
        total = 0
        first_weight = position + 1

        for index in range(position):
            total = total + digits[index] * (first_weight - index)

        remainder = total % 11

        if remainder < 2:
            expected_digit = 0
        else:
            expected_digit = 11 - remainder

        if digits[position] != expected_digit:
            return False

    return True


# ────────────────────────────────────────────────────────────────────
# CNPJ — acrescentado pela party-api (D0010, emenda; guia §14)
# ────────────────────────────────────────────────────────────────────
CNPJ_LENGTH = 14

# Os pesos de cada um dos dois dígitos verificadores do CNPJ. Ao
# contrário do CPF, eles não decrescem em linha reta: vão de 5 (ou 6) até
# 2 e recomeçam em 9.
CNPJ_FIRST_WEIGHTS = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
CNPJ_SECOND_WEIGHTS = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def is_valid_cnpj(document_number: str) -> bool:
    """Diz se um CNPJ existe de verdade — a mesma pergunta do is_valid_cpf.

    O schema da party-api já cobrou o formato: catorze dígitos, sem
    máscara. Aqui é a conta: os dois últimos dígitos são o RESULTADO de
    uma soma ponderada dos anteriores, e um número que erra a conta não é
    CNPJ de ninguém. Por isso a recusa é 422, não 400.

    A regra do resto é a mesma do CPF: resto menor que 2 vira dígito 0;
    nos outros casos, o dígito é 11 menos o resto. O que muda são os pesos,
    na lista lá em cima.
    """
    digits = []
    for character in document_number:
        if character.isdigit():
            digits.append(int(character))

    if len(digits) != CNPJ_LENGTH:
        return False

    # Como no CPF: catorze dígitos iguais passam na conta e não valem.
    all_digits_are_equal = True
    for digit in digits:
        if digit != digits[0]:
            all_digits_are_equal = False
            break

    if all_digits_are_equal:
        return False

    for weights in [CNPJ_FIRST_WEIGHTS, CNPJ_SECOND_WEIGHTS]:
        position = len(weights)
        total = 0

        for index in range(position):
            total = total + digits[index] * weights[index]

        remainder = total % 11

        if remainder < 2:
            expected_digit = 0
        else:
            expected_digit = 11 - remainder

        if digits[position] != expected_digit:
            return False

    return True
