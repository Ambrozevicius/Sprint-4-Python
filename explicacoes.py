"""Consulta REST ao Gemini sob demanda; o resultado oficial permanece local."""

import json
import os
import re
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from calculos import calcular_expressao
from fractions import Fraction
from persistencia import MAX_EXPLICACAO, validar_texto

MODELO_PADRAO = "gemini-3.5-flash-lite"
TIMEOUT = 20
INSTRUCAO = (
    "Você é um tutor de aritmética. Explique a expressão fornecida em português "
    "brasileiro, em até quatro etapas curtas e no máximo 100 palavras. Respeite "
    "parênteses e precedência. Mostre somente as operações necessárias e o resultado "
    "final, sem introdução, elogios, conclusão ou assuntos adicionais. Os operandos "
    "de entrada são inteiros não negativos e as operações permitidas são soma, "
    "subtração, multiplicação e divisão. A expressão e o resultado local estão "
    "abaixo. Se encontrar inconsistência, informe-a em uma frase e não invente justificativas."
)


def gerar_explicacao(expressao, resultado):
    normalizada, calculado = calcular_expressao(expressao)
    if calculado != resultado:
        raise ValueError("Resultado local inconsistente; consulta cancelada.")
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        raise RuntimeError("Configure GEMINI_API_KEY no ambiente para usar a IA. Cálculo e OCR continuam locais.")
    modelo = os.environ.get("GEMINI_MODEL", MODELO_PADRAO).strip()
    if not re.fullmatch(r"[a-zA-Z0-9._-]{1,100}", modelo):
        raise RuntimeError("GEMINI_MODEL inválido. Use apenas o identificador do modelo.")
    corpo = {
        "systemInstruction": {"parts": [{"text": INSTRUCAO}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps({
            "expressao": normalizada, "resultado_local_exato": str(Fraction(resultado))
        }, ensure_ascii=False)}]}],
        "generationConfig": {"maxOutputTokens": 1024},
    }
    pedido = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": chave},
        method="POST",
    )
    try:
        with urlopen(pedido, timeout=TIMEOUT) as resposta:
            if resposta.status != 200:
                raise RuntimeError("Gemini retornou uma resposta HTTP inesperada.")
            bruto = resposta.read(65537)
        if len(bruto) > 65536:
            raise RuntimeError("Resposta Gemini excedeu o tamanho permitido.")
        dados = json.loads(bruto.decode("utf-8"))
    except HTTPError as erro:
        codigo = erro.code
        erro.close()
        mensagens = {
            400: "Solicitação recusada. Verifique chave e modelo.",
            401: "Chave Gemini inválida ou sem autorização.",
            403: "Chave Gemini sem permissão para este recurso.",
            404: "Modelo indisponível. Confira GEMINI_MODEL na documentação Google.",
            429: "Limite de uso Gemini atingido. Tente mais tarde.",
        }
        raise RuntimeError(mensagens.get(codigo, "Serviço Gemini indisponível. Tente mais tarde.")) from None
    except TimeoutError:
        raise RuntimeError("Tempo de espera Gemini esgotado. Tente mais tarde.") from None
    except URLError:
        raise RuntimeError("Não foi possível conectar ao Gemini. Verifique a conexão.") from None
    except (OSError, ValueError, HTTPException, RecursionError):
        raise RuntimeError("Resposta Gemini inválida ou falha de comunicação.") from None
    try:
        if not isinstance(dados, dict):
            raise ValueError
        feedback = dados.get("promptFeedback", {})
        if not isinstance(feedback, dict):
            raise ValueError
        if feedback.get("blockReason"):
            raise RuntimeError("Gemini bloqueou a solicitação; nenhuma explicação foi salva.")
        candidatos = dados.get("candidates")
        if not isinstance(candidatos, list) or not candidatos or not isinstance(candidatos[0], dict):
            raise ValueError
        candidato = candidatos[0]
        if candidato.get("finishReason") != "STOP":
            raise RuntimeError("Gemini não concluiu a explicação (bloqueio ou limite de saída).")
        partes = candidato["content"]["parts"]
        if not isinstance(partes, list):
            raise ValueError
        textos = []
        for parte in partes:
            if not isinstance(parte, dict):
                raise ValueError
            if parte.get("thought"):
                continue
            if not isinstance(parte.get("text"), str):
                raise ValueError
            textos.append(parte["text"])
        texto = "\n".join(textos).strip()
        validar_texto(texto, MAX_EXPLICACAO, "explicacao")
        if len(texto.split()) > 100:
            raise RuntimeError("Explicação excedeu 100 palavras; resposta descartada.")
        return texto
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Gemini retornou resposta vazia ou em formato inesperado.") from None
