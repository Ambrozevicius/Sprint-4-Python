"""Funções de câmera, imagem e OCR do JOVI MATH."""

import os
from pathlib import Path
from uuid import uuid4

from calculos import adicionar_historico, calcular_expressao, formatar_resultado


try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

if cv2 is not None:
    # Evita avisos técnicos no terminal quando o computador não tem webcam.
    cv2.setLogLevel(0)

try:
    from rapidocr import RapidOCR
except ImportError:
    RapidOCR = None


EXTENSOES_SUPORTADAS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
MENSAGEM_OCR_INVALIDO = "Não foi possível identificar uma expressão matemática válida."
_motor_ocr = None
PASTA_PROJETO = Path(__file__).resolve().parent


def dependencias_disponiveis():
    return cv2 is not None and np is not None and RapidOCR is not None


def _abrir_camera(indice=0):
    if cv2 is None:
        return None

    captura = None
    try:
        if os.name == "nt":
            captura = cv2.VideoCapture(indice, cv2.CAP_DSHOW)

        if captura is None or not captura.isOpened():
            if captura is not None:
                captura.release()
            captura = cv2.VideoCapture(indice)

        return captura
    except (cv2.error, KeyboardInterrupt):
        _liberar_camera(captura)
        raise


def _liberar_camera(captura):
    if captura is not None:
        try:
            captura.release()
        except cv2.error:
            print("Aviso: OpenCV não conseguiu liberar a câmera.")


def verificar_camera(indice=0):
    """Verifica a webcam sem manter o dispositivo ocupado."""
    if cv2 is None:
        return False
    captura = None

    try:
        captura = _abrir_camera(indice)
        if captura is None or not captura.isOpened():
            return False

        sucesso, _ = captura.read()
        return bool(sucesso)
    except cv2.error:
        return False
    finally:
        _liberar_camera(captura)


def preparar_imagem(imagem):
    """Aumenta o contraste e o tamanho para facilitar a leitura do OCR."""
    if cv2 is None or np is None:
        raise RuntimeError("As dependências de imagem não estão instaladas.")

    if imagem is None or not isinstance(imagem, np.ndarray) or imagem.size == 0:
        raise ValueError("A imagem informada não pôde ser processada.")

    if len(imagem.shape) == 3:
        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    else:
        cinza = imagem.copy()

    altura, largura = cinza.shape[:2]
    if altura < 300 or largura < 700:
        fator = max(2.0, 700 / max(largura, 1))
        cinza = cv2.resize(cinza, None, fx=fator, fy=fator, interpolation=cv2.INTER_CUBIC)

    suavizada = cv2.GaussianBlur(cinza, (3, 3), 0)
    _, binaria = cv2.threshold(
        suavizada, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return cv2.copyMakeBorder(
        binaria, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255
    )


def _obter_motor_ocr():
    global _motor_ocr

    if RapidOCR is None:
        raise RuntimeError(
            "O OCR não está instalado. Execute: pip install -r requirements.txt"
        )

    if _motor_ocr is None:
        try:
            _motor_ocr = RapidOCR(params={"Global.log_level": "error"})
        except Exception as erro:
            raise RuntimeError("Não foi possível iniciar o OCR.") from erro

    return _motor_ocr


def _extrair_textos(resultado_ocr):
    """RapidOCR 3.9.2 retorna objetos; saída só de detecção não tem txts."""
    return list(getattr(resultado_ocr, "txts", None) or [])


def _avaliar_textos(textos, permitir_juncao=True):
    """Evita transformar duas contas diferentes em uma expressão inventada."""
    textos = [texto.strip() for texto in textos if texto.strip()]
    calculos_individuais = []

    for texto in textos:
        try:
            expressao, resultado = calcular_expressao(texto, origem_ocr=True)
            calculos_individuais.append((expressao, resultado, texto))
        except ValueError:
            continue

    if len(calculos_individuais) > 1:
        raise ValueError(MENSAGEM_OCR_INVALIDO)

    if len(calculos_individuais) == 1:
        if len(textos) == 1:
            return calculos_individuais[0]

        # A única exceção segura é um '=' reconhecido separadamente no final.
        outros = [texto for texto in textos if texto != calculos_individuais[0][2]]
        if all(texto == "=" for texto in outros):
            candidato = "".join(textos)
            expressao, resultado = calcular_expressao(candidato, origem_ocr=True)
            return expressao, resultado, candidato

        raise ValueError(MENSAGEM_OCR_INVALIDO)

    if permitir_juncao and len(textos) > 1:
        # Espaços preservam a separação de algarismos detectados em blocos distintos.
        candidato = " ".join(textos)
        try:
            expressao, resultado = calcular_expressao(candidato, origem_ocr=True)
            return expressao, resultado, candidato
        except ValueError:
            return None

    return None


def reconhecer_e_calcular(imagem):
    """Executa OCR e retorna expressão normalizada, resultado e texto bruto."""
    if not dependencias_disponiveis():
        raise RuntimeError(
            "As dependências de câmera e OCR não estão instaladas. "
            "Execute: pip install -r requirements.txt"
        )

    motor = _obter_motor_ocr()
    versoes_imagem = [imagem, preparar_imagem(imagem)]
    ultimo_erro = None

    for versao in versoes_imagem:
        # Blocos rejeitam contas distintas; linha inteira preserva barras de divisão.
        for detectar_blocos in (True, False):
            try:
                # O motor mantém opções entre chamadas: defina cada modo por completo.
                leitura = motor(versao, use_det=detectar_blocos,
                               use_cls=detectar_blocos, use_rec=True)
            except Exception as erro:
                # Falhas do motor permitem tentar a próxima leitura, sem ocultar a causa.
                ultimo_erro = erro
                continue
            calculo = _avaliar_textos(
                _extrair_textos(leitura), permitir_juncao=detectar_blocos
            )
            if calculo is not None:
                return calculo

    if ultimo_erro is not None:
        raise RuntimeError("Falha no motor OCR. Tente outra imagem ou reinicie o programa.") from ultimo_erro
    raise ValueError(MENSAGEM_OCR_INVALIDO)


def carregar_imagem(caminho_digitado):
    """Valida e carrega uma imagem, inclusive em caminhos Unicode do Windows."""
    if cv2 is None or np is None:
        raise RuntimeError(
            "As dependências de imagem não estão instaladas. "
            "Execute: pip install -r requirements.txt"
        )

    caminho_limpo = str(caminho_digitado).strip().strip('"').strip("'")
    if caminho_limpo == "":
        raise ValueError("O caminho da imagem não pode ficar vazio.")

    caminho = Path(caminho_limpo).expanduser()
    if not caminho.is_absolute():
        caminho = PASTA_PROJETO / caminho
    if not caminho.is_file():
        raise FileNotFoundError("Arquivo de imagem não encontrado.")

    if caminho.suffix.lower() not in EXTENSOES_SUPORTADAS:
        raise ValueError(
            "Formato não suportado. Use PNG, JPG, JPEG, BMP ou WEBP."
        )

    try:
        dados = np.fromfile(str(caminho), dtype=np.uint8)
        imagem = cv2.imdecode(dados, cv2.IMREAD_COLOR)
    except (OSError, cv2.error) as erro:
        raise ValueError("Não foi possível ler a imagem. Confira o arquivo e as permissões.") from erro

    if imagem is None:
        raise ValueError("O arquivo existe, mas não contém uma imagem válida.")

    return imagem


def processar_arquivo(caminho):
    imagem = carregar_imagem(caminho)
    return reconhecer_e_calcular(imagem)


def _desenhar_interface_camera(frame, area, mensagem):
    x1, y1, x2, y2 = area
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(
        frame,
        "Posicione a expressao no retangulo",
        (x1, max(30, y1 - 38)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "ESPACO: analisar | S: salvar recorte | ESC/Q: sair",
        (x1, max(55, y1 - 12)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )

    if mensagem:
        cv2.rectangle(frame, (x1, y2 + 10), (x2, y2 + 50), (0, 0, 0), -1)
        cv2.putText(
            frame,
            mensagem,
            (x1 + 10, y2 + 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def salvar_recorte(recorte, pasta=PASTA_PROJETO / "capturas"):
    """Codificação OpenCV e escrita exclusiva suportam caminhos Unicode no Windows."""
    if cv2 is None or np is None:
        return False, "Dependências de imagem indisponíveis."
    if recorte is None or not isinstance(recorte, np.ndarray) or recorte.size == 0:
        return False, "Analise uma expressão válida com ESPAÇO antes de salvar."
    caminho = None
    criado = False
    try:
        sucesso, dados = cv2.imencode(".png", recorte)
        if not sucesso:
            return False, "OpenCV não conseguiu codificar o recorte. Nada foi salvo."
        pasta = Path(pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"recorte-{uuid4().hex}.png"
        with caminho.open("xb") as arquivo:
            criado = True
            arquivo.write(dados.tobytes())
            arquivo.flush()
            os.fsync(arquivo.fileno())
        return True, f"Recorte salvo em {caminho}"
    except (OSError, cv2.error):
        if criado:
            try:
                caminho.unlink(missing_ok=True)
            except OSError:
                pass
        return False, "Não foi possível salvar o recorte. Verifique a pasta e as permissões."


def resolver_por_camera(historico, indice=0, ao_calcular=None, pasta_capturas=PASTA_PROJETO / "capturas"):
    """Abre a webcam e analisa a região central somente ao pressionar ESPAÇO."""
    if not dependencias_disponiveis():
        print(
            "\nAs dependências de câmera e OCR não estão instaladas. "
            "Execute: pip install -r requirements.txt"
        )
        return False

    captura = None
    janela = "JOVI MATH - Camera"
    mensagem = ""
    ultimo_recorte = None

    try:
        captura = _abrir_camera(indice)
        if captura is None or not captura.isOpened():
            print("\nNenhuma câmera foi encontrada.")
            print("Use a opção por imagem ou a opção de cálculo digitado.")
            return False
        print("ESPAÇO analisa; S salva o último recorte válido analisado; ESC/Q sai.")
        print("Para Ver explicação, saia da câmera e use a opção 12 no terminal.")

        while True:
            sucesso, frame = captura.read()
            if not sucesso:
                print("\nNão foi possível receber a imagem da câmera.")
                return False

            altura, largura = frame.shape[:2]
            x1 = int(largura * 0.10)
            x2 = int(largura * 0.90)
            y1 = int(altura * 0.32)
            y2 = int(altura * 0.68)
            area = (x1, y1, x2, y2)

            exibicao = frame.copy()
            _desenhar_interface_camera(exibicao, area, mensagem)
            cv2.imshow(janela, exibicao)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (27, ord("q"), ord("Q")):
                return True
            if tecla in (ord("s"), ord("S")):
                salvo, aviso = salvar_recorte(ultimo_recorte, pasta_capturas)
                print(aviso)
                mensagem = "Recorte salvo." if salvo else "Recorte nao salvo. Veja o terminal."

            if tecla == 32:
                # Uma tentativa nova invalida a anterior, inclusive quando o OCR falha.
                ultimo_recorte = None
                recorte = frame[y1:y2, x1:x2].copy()
                try:
                    expressao, resultado, _ = reconhecer_e_calcular(recorte)
                    ultimo_recorte = recorte
                    if ao_calcular is None:
                        adicionar_historico(historico, expressao, resultado, "camera")
                    else:
                        ao_calcular(expressao, resultado, "camera")
                    mensagem = f"Resultado: {formatar_resultado(resultado)}"
                    print(f"\n{expressao} = {formatar_resultado(resultado)}")
                    print("S salva o recorte desta análise; nenhuma imagem foi salva automaticamente.")
                except ZeroDivisionError as erro:
                    mensagem = "Divisao por zero. Tente novamente."
                    print(f"\n{erro}")
                except (ValueError, RuntimeError) as erro:
                    mensagem = "Leitura invalida. Tente novamente."
                    print(f"\n{erro}")
    except cv2.error:
        print("\nOcorreu um erro ao acessar a câmera. Use imagem ou cálculo digitado.")
        return False
    finally:
        _liberar_camera(captura)
        try:
            cv2.destroyWindow(janela)
        except cv2.error:
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass  # A janela pode não ter sido aberta.
