"""JOVI MATH - Sprint 4 de Computational Thinking with Python."""

from pathlib import Path
from io import StringIO
from calculos import (
    calcular_expressao,
    contar_origens,
    formatar_resultado,
)
from camera_ocr import processar_arquivo, resolver_por_camera, verificar_camera
from configuracoes import PADROES, carregar_configuracoes, salvar_configuracoes
from explicacoes import gerar_explicacao
from persistencia import (
    PASTA_PROJETO, iniciar_historico, registrar_calculo, atualizar_explicacao,
    limpar_historico, exportar_historico,
)


LINHA = "------------------------------------------------------------"
INTEGRANTES = [
    "Isaac Ambrozevicius - RM569166",
    "João Marenov - RM569562",
    "Thalles Almeida - RM569925",
    "Murillo Farias - RM569045",
]


def pausa():
    input("\nAperte ENTER para voltar ao menu")


def cabecalho(titulo):
    print(f"\n{LINHA}\n{titulo}\n{LINHA}")


def mostrar_menu(camera_disponivel):
    status = "DISPONÍVEL" if camera_disponivel else "INDISPONÍVEL"
    print(f"\n{LINHA}")
    print("JOVI MATH")
    print("Reconhecimento de cálculos pela câmera")
    print(f"Status da câmera: {status}")
    print(LINHA)
    print("1 - Sobre o projeto")
    print("2 - Resolver cálculo pela câmera")
    print("3 - Resolver cálculo por imagem")
    print("4 - Resolver cálculo digitado")
    print("5 - Ver histórico")
    print("6 - Estatísticas")
    print("7 - Apagar histórico")
    print("8 - Integrantes")
    print("9 - Sair")
    print("10 - Configurações")
    print("11 - Exportar histórico JSON para a equipe Web")
    print("12 - Ver explicação de um registro")
    print(LINHA)


def validar_opcao_menu(texto, minimo, maximo):
    while True:
        try:
            opcao = int(input(texto))
            if minimo <= opcao <= maximo:
                return opcao
            print(f"Opção inválida. Escolha de {minimo} até {maximo}.")
        except ValueError:
            print("Digite apenas o número de uma opção do menu.")


def sobre_projeto():
    cabecalho("SOBRE O PROJETO")
    print(
        "O JOVI MATH é uma prova de conceito em Python voltada para "
        "estudantes.\nEle usa câmera e OCR para reconhecer cálculos simples "
        "e mostrar o resultado.\nEm um produto final, a função seria integrada "
        "à câmera de um smartphone JOVI,\nsem exigir que uma foto do exercício "
        "seja salva na galeria."
    )


def mostrar_integrantes():
    cabecalho("INTEGRANTES")
    for integrante in INTEGRANTES:
        print(integrante)


def mostrar_calculo(estado, preferencias, expressao, resultado, origem):
    print(f"\n{expressao} = {formatar_resultado(resultado)}")
    registro = registrar_calculo(estado, expressao, resultado, origem, preferencias["salvar_historico"])
    if registro is not None and confirmar("Ver explicação gerada por IA?"):
        ver_explicacao(estado, preferencias, registro)


def resolver_digitado(estado, preferencias):
    cabecalho("RESOLVER CÁLCULO DIGITADO")
    expressao_digitada = input("Digite a expressão: ")

    try:
        expressao, resultado = calcular_expressao(expressao_digitada)
    except (ZeroDivisionError, ValueError) as erro:
        print(f"\n{erro}")
    else:
        mostrar_calculo(estado, preferencias, expressao, resultado, "digitado")


def resolver_imagem(estado, preferencias):
    cabecalho("RESOLVER CÁLCULO POR IMAGEM")
    caminho = input("Caminho da imagem: ")

    try:
        expressao, resultado, _ = processar_arquivo(caminho)
    except (OSError, ValueError, RuntimeError, ZeroDivisionError) as erro:
        print(f"\n{erro}")
    else:
        mostrar_calculo(estado, preferencias, expressao, resultado, "imagem")


def mostrar_historico(historico, persistidos=()):
    cabecalho("HISTÓRICO SALVO E DA SESSÃO")

    if len(historico) == 0:
        print("Nenhum cálculo no histórico.")
        return

    salvos_por_id = {r["id"]: r for r in persistidos}
    for indice, registro in enumerate(historico, start=1):
        resultado = formatar_resultado(registro["resultado"])
        print(f"{indice} - {registro['expressao']} = {resultado}")
        print(f"    Origem: {registro['origem']}")
        print(f"    Data/hora: {registro['data_hora']}")
        salvo = salvos_por_id.get(registro["id"])
        print("    Registro salvo" if salvo else "    Temporário: somente nesta sessão")
        if registro["explicacao"]:
            status = "salva" if salvo and salvo["explicacao"] == registro["explicacao"] else "somente na sessão"
            print(f"    Explicação gerada por IA disponível ({status}); opção 12 para consultar.")


def mostrar_estatisticas(historico):
    cabecalho("ESTATÍSTICAS")

    if len(historico) == 0:
        print("Nenhum cálculo foi realizado nesta execução.")
        return

    quantidades = contar_origens(historico)
    print(f"Total de cálculos: {len(historico)}")
    print(f"Pela câmera: {quantidades['camera']}")
    print(f"Por imagem: {quantidades['imagem']}")
    print(f"Digitados: {quantidades['digitado']}")


def apagar_historico(estado):
    cabecalho("APAGAR HISTÓRICO")

    print("Remove os registros salvos e da sessão, mesmo com salvamento automático desligado.")
    print("Capturas, exportações e cópias de segurança não serão apagadas.")
    if confirmar("Deseja realmente apagar o histórico?"):
        sucesso, mensagem = limpar_historico(estado)
        print(mensagem)
        return sucesso
    print("O histórico foi mantido.")
    return False


def confirmar(pergunta):
    while True:
        resposta = input(f"{pergunta} (S/N): ").strip().upper()
        if resposta in ("S", "N"):
            return resposta == "S"
        print("Resposta inválida. Digite S ou N.")


def ver_explicacao(estado, preferencias, registro=None):
    if registro is None:
        if not estado["historico"]:
            print("Nenhum cálculo disponível para explicar.")
            return
        mostrar_historico(estado["historico"], estado["persistidos"])
        indice = validar_opcao_menu("Número do registro (0 para voltar): ", 0, len(estado["historico"]))
        if indice == 0:
            return
        registro = estado["historico"][indice - 1]
    print(f"Resultado oficial local: {registro['expressao']} = {formatar_resultado(registro['resultado'])}")
    if registro["explicacao"]:
        print(f"Explicação gerada por IA:\n{registro['explicacao']}")
        if not confirmar("Gerar outra explicação consultando o Gemini novamente?"):
            return
    else:
        print("A consulta envia somente a expressão e o resultado local ao Gemini.")
    try:
        texto = gerar_explicacao(registro["expressao"], registro["resultado"])
    except (RuntimeError, ValueError) as erro:
        print(f"Explicação indisponível: {erro}")
        return
    atualizar_explicacao(estado, registro, texto, preferencias["salvar_historico"])
    print(f"Explicação gerada por IA:\n{texto}")


def configurar(preferencias, controle):
    while True:
        print(f"\nÍndice da câmera: {preferencias['indice_camera']}")
        print(f"Salvar histórico automaticamente: {preferencias['salvar_historico']}")
        print("Desativar mantém os dados já salvos. Novos registros e novas explicações ficam na sessão.")
        print("Reativar não grava retroativamente registros ou explicações temporários.")
        print("1 - Alterar câmera | 2 - Alternar salvamento | 3 - Restaurar padrões | 0 - Voltar")
        opcao = validar_opcao_menu("Opção: ", 0, 3)
        if opcao == 0:
            return
        novas = preferencias.copy()
        if opcao == 1:
            novas["indice_camera"] = validar_opcao_menu("Índice da câmera (0 a 99): ", 0, 99)
        elif opcao == 2:
            novas["salvar_historico"] = not preferencias["salvar_historico"]
            if not confirmar(f"Alterar salvamento para {novas['salvar_historico']}?"):
                continue
        elif confirmar("Restaurar câmera 0 e salvamento automático ligado?"):
            novas = PADROES.copy()
        else:
            continue
        sucesso, mensagem = salvar_configuracoes(controle, novas)
        preferencias.update(novas)
        print(mensagem)
        if not sucesso:
            print("Preferências alteradas somente nesta sessão.")


def executar(pasta=PASTA_PROJETO):
    pasta = Path(pasta)
    estado = iniciar_historico(pasta)
    preferencias, controle_config = carregar_configuracoes(pasta)
    historico = estado["historico"]
    camera_disponivel = verificar_camera(preferencias["indice_camera"])

    while True:
        mostrar_menu(camera_disponivel)

        try:
            opcao = validar_opcao_menu("Escolha uma opção: ", 1, 12)

            if opcao == 1:
                sobre_projeto()
            elif opcao == 2:
                cabecalho("RESOLVER CÁLCULO PELA CÂMERA")
                def registrar_camera(expressao, resultado, origem):
                    return registrar_calculo(estado, expressao, resultado, origem, preferencias["salvar_historico"])
                resolver_por_camera(historico, preferencias["indice_camera"], registrar_camera, pasta / "capturas")
                camera_disponivel = verificar_camera(preferencias["indice_camera"])
            elif opcao == 3:
                resolver_imagem(estado, preferencias)
            elif opcao == 4:
                resolver_digitado(estado, preferencias)
            elif opcao == 5:
                mostrar_historico(historico, estado["persistidos"])
            elif opcao == 6:
                mostrar_estatisticas(historico)
            elif opcao == 7:
                apagar_historico(estado)
            elif opcao == 8:
                mostrar_integrantes()
            elif opcao == 9:
                print("\nEncerrando o JOVI MATH.")
                print("Obrigado por utilizar o programa!")
                break
            elif opcao == 10:
                configurar(preferencias, controle_config)
                camera_disponivel = verificar_camera(preferencias["indice_camera"])
            elif opcao == 11:
                print("Exportação manual inclui todos os registros visíveis, inclusive temporários.")
                print("Não inclui imagens, caminhos locais, configurações ou credenciais.")
                if confirmar("Exportar agora?"):
                    _, mensagem = exportar_historico(estado, pasta)
                    print(mensagem)
            elif opcao == 12:
                ver_explicacao(estado, preferencias)

            pausa()


        except (EOFError, KeyboardInterrupt):
            print("\n\nExecução encerrada pelo usuário.")
            break


def carregar_ambiente(pasta=PASTA_PROJETO):
    """Lê o arquivo inteiro antes de aplicar variáveis; nunca mostra seu conteúdo."""
    try:
        conteudo = (Path(pasta) / ".env").read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return
    except (OSError, UnicodeError):
        print("Aviso: não foi possível ler .env. Confira permissões e codificação UTF-8. "
              "O cálculo local continua disponível; variáveis do ambiente permanecem válidas.")
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Aviso: instale requirements.txt para carregar .env. O cálculo local continua disponível.")
        return

    # Usa somente o .env do projeto; variáveis já definidas no ambiente prevalecem.
    load_dotenv(stream=StringIO(conteudo), override=False)


if __name__ == "__main__":
    try:
        carregar_ambiente()
        executar()
    except (EOFError, KeyboardInterrupt):
        print("\nExecução encerrada pelo usuário.")
