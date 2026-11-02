"""Funções de validação, cálculo e histórico do JOVI MATH."""
import ast
from datetime import datetime
from fractions import Fraction
import re
from uuid import uuid4


OPERADORES_PERMITIDOS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
MENSAGEM_EXPRESSAO_INVALIDA = "Expressão matemática inválida."


def normalizar_expressao(texto, origem_ocr=False):
    """Padroniza operadores sem tentar adivinhar números reconhecidos pelo OCR."""
    if texto is None:
        raise ValueError("A expressão não pode ficar vazia.")
    if not isinstance(texto, str) or len(texto) > 1000:
        raise ValueError("Informe uma expressão de texto com até 1000 caracteres.")

    expressao = texto.strip()

    if origem_ocr:
        # Um sinal de igual no final é comum em imagens de exercícios.
        expressao = re.sub(r"=\s*$", "", expressao)

    trocas = {
        "x": "*",
        "X": "*",
        "×": "*",
        "÷": "/",
        "−": "-",
        "–": "-",
        "—": "-",
    }

    for antigo, novo in trocas.items():
        expressao = expressao.replace(antigo, novo)

    if re.search(r"\d\s+\d", expressao):
        raise ValueError("Não separe os algarismos de um mesmo número.")

    expressao = re.sub(r"\s+", "", expressao)

    if expressao == "":
        raise ValueError("A expressão não pode ficar vazia.")

    if len(expressao) > 200:
        raise ValueError("A expressão é muito longa.")

    if "." in expressao or "," in expressao:
        raise ValueError("Números decimais não são permitidos na entrada.")

    if re.fullmatch(r"[0-9+\-*/()]+", expressao) is None:
        raise ValueError(
            "Use somente números inteiros, parênteses e os operadores +, -, * e /."
        )

    if not any(operador in expressao for operador in "+-*/"):
        raise ValueError("Informe uma expressão com pelo menos uma operação.")

    # Converte, por exemplo, "08" em "8" antes do parser. Isso é útil no OCR,
    # pois zeros à esquerda não alteram o valor, mas não fazem parte da sintaxe
    # aceita pelo parser do Python.
    expressao = re.sub(r"\d+", lambda numero: str(int(numero.group())), expressao)

    return expressao


def _calcular_no(no):
    """Percorre somente os nós seguros da árvore da expressão."""
    if isinstance(no, ast.Expression):
        return _calcular_no(no.body)

    if isinstance(no, ast.Constant):
        if type(no.value) is not int or no.value < 0:
            raise ValueError("Os operandos devem ser números inteiros não negativos.")
        return no.value

    if isinstance(no, ast.BinOp):
        if not isinstance(no.op, OPERADORES_PERMITIDOS):
            raise ValueError("Somente soma, subtração, multiplicação e divisão são aceitas.")

        esquerda = _calcular_no(no.left)
        direita = _calcular_no(no.right)

        if isinstance(no.op, ast.Add):
            return esquerda + direita
        if isinstance(no.op, ast.Sub):
            return esquerda - direita
        if isinstance(no.op, ast.Mult):
            return esquerda * direita
        if isinstance(no.op, ast.Div):
            if direita == 0:
                raise ZeroDivisionError("Não é possível realizar divisão por zero.")
            # Fraction evita perda de precisão antes da formatação final.
            return Fraction(esquerda) / Fraction(direita)

    # Rejeita operadores unários, nomes, chamadas de função e qualquer outro nó.
    raise ValueError(MENSAGEM_EXPRESSAO_INVALIDA)


def calcular_expressao(texto, origem_ocr=False):
    """Normaliza e calcula uma expressão sem executar texto como código."""
    expressao = normalizar_expressao(texto, origem_ocr)

    try:
        arvore = ast.parse(expressao, mode="eval")
    except (SyntaxError, MemoryError):
        raise ValueError(MENSAGEM_EXPRESSAO_INVALIDA) from None

    try:
        resultado = _calcular_no(arvore)
    except RecursionError:
        raise ValueError("A expressão possui parênteses ou operações em excesso.") from None
    except OverflowError:
        raise ValueError("Os números informados são grandes demais.") from None

    return expressao, resultado


def formatar_resultado(resultado):
    """Exibe inteiros sem casas e resultados decimais com duas casas."""
    if isinstance(resultado, int):
        return str(resultado)

    if isinstance(resultado, Fraction):
        if resultado.denominator == 1:
            return str(resultado.numerator)

        sinal = "-" if resultado < 0 else ""
        numerador = abs(resultado.numerator)
        denominador = resultado.denominator
        parte_inteira, resto = divmod(numerador, denominador)
        centesimos, resto_arredondamento = divmod(resto * 100, denominador)

        if resto_arredondamento * 2 >= denominador:
            centesimos += 1
        if centesimos == 100:
            parte_inteira += 1
            centesimos = 0
        if parte_inteira == 0 and centesimos == 0:
            sinal = ""

        return f"{sinal}{parte_inteira}.{centesimos:02d}"

    if isinstance(resultado, float) and resultado.is_integer():
        return str(int(resultado))

    return f"{resultado:.2f}"


def adicionar_historico(historico, expressao, resultado, origem):
    """Adiciona um dicionário à lista de cálculos da execução atual."""
    registro = {
        "id": str(uuid4()),
        "expressao": expressao,
        "resultado": resultado,
        "origem": origem,
        "data_hora": datetime.now().astimezone().isoformat(timespec="seconds"),
        "explicacao": None,
    }
    historico.append(registro)
    return registro


def contar_origens(historico):
    """Retorna as quantidades de cálculos feitos por cada origem."""
    quantidades = {"camera": 0, "imagem": 0, "digitado": 0}

    for registro in historico:
        origem = registro.get("origem")
        if origem in quantidades:
            quantidades[origem] += 1

    return quantidades
