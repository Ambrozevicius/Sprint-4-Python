"""Preferências simples, sem credenciais."""

from pathlib import Path
from persistencia import PASTA_PROJETO, carregar_json, gravar_json

PADROES = {"indice_camera": 0, "salvar_historico": True}


def validar_configuracoes(dados):
    if not isinstance(dados, dict) or set(dados) != set(PADROES):
        raise ValueError("Configuração com campos inválidos.")
    if type(dados["indice_camera"]) is not int or not 0 <= dados["indice_camera"] <= 99:
        raise ValueError("Índice da câmera deve ser inteiro entre 0 e 99.")
    if type(dados["salvar_historico"]) is not bool:
        raise ValueError("Salvar histórico deve ser booleano.")
    return dados.copy()


def carregar_configuracoes(pasta=PASTA_PROJETO):
    return carregar_json(Path(pasta) / "dados/configuracoes.json", PADROES, validar_configuracoes)


def salvar_configuracoes(controle, preferencias):
    validar_configuracoes(preferencias)
    return gravar_json(controle, preferencias)
