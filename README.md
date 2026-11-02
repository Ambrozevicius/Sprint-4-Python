# JOVI MATH — Sprint 4

Prova de conceito em Python para reconhecer e resolver expressões matemáticas por **webcam, imagem ou digitação**.  
A Sprint 4 adiciona histórico persistente, configurações, captura opcional, explicações via Gemini e exportação JSON para integração Web.

## Executar

Requisitos: **Windows 10/11** e **Python 3.12 64 bits**.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Principais recursos

- OCR local com RapidOCR.
- Cálculo seguro de `+`, `-`, `*`, `/` e parênteses.
- Histórico e configurações persistidos em JSON.
- Captura opcional do recorte da webcam.
- Explicações matemáticas opcionais via Gemini.
- Exportação do histórico em JSON para a equipe Web.

## Gemini

Copie `.env.example` para `.env` e preencha `GEMINI_API_KEY`.

```powershell
Copy-Item .env.example .env
```

Sem chave ou internet, o cálculo local continua funcionando normalmente.

## Integração Web

Os arquivos de referência estão em `integracao_web/`.  
A opção **11** exporta o histórico para JSON, que pode ser carregado pelo frontend.

## Integrantes

Consulte `INTEGRANTES.txt`.