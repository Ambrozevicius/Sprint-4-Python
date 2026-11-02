"""JSON validado e gravação atômica, sem misturar registros salvos e temporários."""

from datetime import datetime
from fractions import Fraction
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from uuid import uuid4

from calculos import adicionar_historico, calcular_expressao, formatar_resultado

PASTA_PROJETO = Path(__file__).resolve().parent
MAX_BYTES = 5 * 1024 * 1024
MAX_REGISTROS = 1000
MAX_EXPLICACAO = 2000


def agora():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def validar_data(valor):
    if not isinstance(valor, str) or len(valor) > 40 or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", valor
    ):
        raise ValueError("Data deve usar ISO 8601 com fuso.")
    data = datetime.fromisoformat(valor)
    if data.utcoffset() is None or (
        not valor.endswith("Z") and (int(valor[-5:-3]) > 23 or int(valor[-2:]) > 59)
    ):
        raise ValueError("Fuso horário inválido.")
    return valor


def validar_texto(valor, limite, campo):
    if not isinstance(valor, str) or not valor.strip() or len(valor) > limite:
        raise ValueError(f"Campo {campo} inválido.")
    if any((ord(c) < 32 and c not in "\n\t") or ord(c) == 127
           or 0xD800 <= ord(c) <= 0xDFFF for c in valor):
        raise ValueError(f"Campo {campo} contém controles inválidos.")
    return valor


def registro_publico(registro):
    """Fraction só se torna string na fronteira com JSON."""
    return {
        "id": registro["id"],
        "expressao": registro["expressao"],
        "resultado_exato": str(Fraction(registro["resultado"])),
        "resultado_formatado": formatar_resultado(registro["resultado"]),
        "origem": registro["origem"],
        "data_hora": registro["data_hora"],
        "explicacao": registro["explicacao"],
    }


def criar_documento(registros):
    return {
        "versao_schema": 1,
        "projeto": "JOVI MATH",
        "exportado_em": agora(),
        "registros": [registro_publico(r) for r in registros],
    }


def validar_documento(dados):
    if not isinstance(dados, dict) or set(dados) != {
        "versao_schema", "projeto", "exportado_em", "registros"
    }:
        raise ValueError("Estrutura do documento inválida.")
    if type(dados["versao_schema"]) is not int or dados["versao_schema"] != 1:
        raise ValueError("Versão de esquema desconhecida; esperado 1.")
    if dados["projeto"] != "JOVI MATH":
        raise ValueError("Projeto desconhecido.")
    validar_data(dados["exportado_em"])
    registros = dados["registros"]
    if not isinstance(registros, list) or len(registros) > MAX_REGISTROS:
        raise ValueError("Histórico deve ser lista com até 1000 registros.")
    convertidos, ids = [], set()
    campos = {"id", "expressao", "resultado_exato", "resultado_formatado",
              "origem", "data_hora", "explicacao"}
    for registro in registros:
        if not isinstance(registro, dict) or set(registro) != campos:
            raise ValueError("Registro com campos inesperados ou ausentes.")
        identificador = validar_texto(registro["id"], 80, "id")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", identificador) or identificador in ids:
            raise ValueError("ID inválido ou duplicado.")
        ids.add(identificador)
        texto = validar_texto(registro["expressao"], 200, "expressao")
        expressao, resultado = calcular_expressao(texto)
        if expressao != texto:
            raise ValueError("Expressão não normalizada.")
        exato = validar_texto(registro["resultado_exato"], 512, "resultado_exato")
        formatado = validar_texto(registro["resultado_formatado"], 512, "resultado_formatado")
        if exato != str(Fraction(resultado)) or formatado != formatar_resultado(resultado):
            raise ValueError("Resultado inconsistente com o cálculo local.")
        if registro["origem"] not in ("camera", "imagem", "digitado"):
            raise ValueError("Origem desconhecida.")
        validar_data(registro["data_hora"])
        explicacao = registro["explicacao"]
        if explicacao is not None:
            validar_texto(explicacao, MAX_EXPLICACAO, "explicacao")
        convertidos.append({
            "id": identificador, "expressao": expressao, "resultado": Fraction(resultado),
            "origem": registro["origem"], "data_hora": registro["data_hora"],
            "explicacao": explicacao,
        })
    return convertidos


def _objeto_sem_duplicatas(pares):
    objeto = {}
    for chave, valor in pares:
        if chave in objeto:
            raise ValueError("JSON contém chave duplicada.")
        objeto[chave] = valor
    return objeto


def carregar_json(caminho, padrao, validar):
    """Retorna valor validado e controle de escrita; nunca descarta arquivo inválido."""
    caminho = Path(caminho)
    controle = {"caminho": caminho, "bloqueado": False}
    try:
        with caminho.open("rb") as arquivo:
            bruto = arquivo.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return padrao.copy(), controle
    except OSError:
        controle["bloqueado"] = True
        print(f"Aviso: não foi possível ler {caminho.name}. Gravação bloqueada; uso em memória.")
        return padrao.copy(), controle
    try:
        if len(bruto) > MAX_BYTES:
            raise ValueError("Arquivo maior que 5 MiB.")
        dados = json.loads(bruto.decode("utf-8"), object_pairs_hook=_objeto_sem_duplicatas)
        return validar(dados), controle
    except (ValueError, TypeError, KeyError, RecursionError, ZeroDivisionError):
        copia = caminho.with_name(f"{caminho.name}.corrompido-{uuid4().hex}.bak")
        try:
            # Cópia binária preserva inclusive codificação inválida e arquivos grandes.
            with caminho.open("rb") as origem, copia.open("xb") as destino:
                shutil.copyfileobj(origem, destino)
                destino.flush()
                os.fsync(destino.fileno())
            print(f"Aviso: {caminho.name} inválido. Bytes preservados em {copia.name}.")
            print("Usando padrões em memória; a próxima gravação poderá recriar o JSON.")
        except OSError:
            controle["bloqueado"] = True
            print(f"Aviso: {caminho.name} inválido e cópia de segurança indisponível.")
            print("Gravação bloqueada para preservar o original. Uso somente em memória.")
        return padrao.copy(), controle


def gravar_json(controle, dados):
    """O temporário fica no mesmo volume; falha mantém o destino anterior."""
    if controle["bloqueado"]:
        return False, "Gravação bloqueada para preservar o arquivo original."
    caminho = controle["caminho"]
    temporario = None
    try:
        conteudo = json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
        if len(conteudo) > MAX_BYTES:
            return False, "Limite de 5 MiB excedido; arquivo anterior mantido."
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=caminho.parent, prefix=".jovi-", suffix=".tmp",
                                         delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
        return True, f"Salvo em {caminho}"
    except (OSError, ValueError, TypeError):
        return False, f"Não foi possível gravar {caminho.name}. Arquivo anterior mantido."
    finally:
        if temporario is not None:
            try:
                temporario.unlink(missing_ok=True)
            except OSError:
                pass


def iniciar_historico(pasta=PASTA_PROJETO):
    registros, controle = carregar_json(Path(pasta) / "dados/historico.json", [], validar_documento)
    # Os campos são imutáveis; basta separar os dicionários da sessão e do disco.
    return {"historico": registros, "persistidos": [r.copy() for r in registros], "controle": controle}


def _salvar_historico(estado, registros):
    sucesso, mensagem = gravar_json(estado["controle"], criar_documento(registros))
    if sucesso:
        estado["persistidos"] = registros
    return sucesso, mensagem


def registrar_calculo(estado, expressao, resultado, origem, salvar=True):
    if len(estado["historico"]) >= MAX_REGISTROS:
        print("Limite de 1000 registros atingido. Exporte e limpe o histórico para registrar novos cálculos.")
        return None
    registro = adicionar_historico(estado["historico"], expressao, resultado, origem)
    if salvar:
        candidatos = estado["persistidos"] + [registro.copy()]
        sucesso, mensagem = _salvar_historico(estado, candidatos)
        if not sucesso:
            print(f"Aviso de persistência: {mensagem} Cálculo mantido somente nesta sessão.")
    return registro


def atualizar_explicacao(estado, registro, texto, salvar=True):
    registro["explicacao"] = texto
    if not salvar:
        return
    for indice, candidato in enumerate(estado["persistidos"]):
        if candidato["id"] == registro["id"]:
            # Altera somente a explicação pedida, sem promover dados temporários.
            candidatos = estado["persistidos"].copy()
            candidatos[indice] = dict(candidato, explicacao=texto)
            sucesso, mensagem = _salvar_historico(estado, candidatos)
            if not sucesso:
                print(f"Aviso de persistência: {mensagem} Explicação somente nesta sessão.")
            return


def limpar_historico(estado):
    sucesso, mensagem = _salvar_historico(estado, [])
    if sucesso:
        estado["historico"].clear()
        return True, "Histórico salvo e da sessão apagados. Capturas e cópias de segurança mantidas."
    return False, f"{mensagem} Histórico da sessão também foi mantido."


def exportar_historico(estado, pasta=PASTA_PROJETO):
    caminho = Path(pasta) / "exportacoes" / f"historico-{uuid4().hex}.json"
    dados = criar_documento(estado["historico"])
    validar_documento(dados)
    return gravar_json({"caminho": caminho, "bloqueado": False}, dados)
