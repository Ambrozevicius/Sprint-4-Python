# Contrato JSON 1 — JOVI MATH

Fluxo: Python exporta pela opção 11; o usuário seleciona esse arquivo no navegador.
O frontend apenas exibe o histórico. Não há upload, servidor Python, sincronização
nem acesso automático do navegador ao disco. O Python não importa estes arquivos.

Todos os campos abaixo são obrigatórios; campos extras são rejeitados pela referência.
O arquivo usa UTF-8 e pode ter até **5 MiB (5.242.880 bytes)** e **1.000 registros**.

| Campo da raiz | Tipo | Validação |
| --- | --- | --- |
| versao_schema | inteiro | Exatamente 1; booleanos e versões desconhecidas são inválidos |
| projeto | string | Exatamente `JOVI MATH` |
| exportado_em | string | Data real ISO 8601 com fuso, por exemplo `2026-10-20T10:00:00-03:00` |
| registros | lista | Pode ser vazia; contém somente registros válidos |

| Campo do registro | Tipo | Validação |
| --- | --- | --- |
| id | string | 1 a 80 caracteres ASCII alfanuméricos, `_` ou `-`; único no arquivo; Python gera UUID |
| expressao | string | Até 200 pontos de código Unicode; normalizada, sem espaços ou zeros à esquerda; operandos inteiros não negativos; `+ - * / ( )`; pelo menos uma operação |
| resultado_exato | string | Até 512 pontos de código Unicode; inteiro canônico ou fração simplificada com denominador positivo; exemplos `16`, `-3`, `5/2` |
| resultado_formatado | string | Até 512 pontos de código Unicode; inteiro sem casas ou fração não inteira arredondada para duas casas com ponto |
| origem | string | `camera`, `imagem` ou `digitado` |
| data_hora | string | ISO 8601 com fuso, calendário válido, até 40 caracteres |
| explicacao | string ou null | Texto não vazio com até 2.000 pontos de código Unicode ou null; conteúdo de IA não é resultado oficial |

Datas têm segundos obrigatórios, frações de segundo opcionais (até seis casas) e
fuso `Z` ou `±HH:MM`. A execução gera as datas efetivas no fuso do computador.
São rejeitados campos de texto vazios e controles invisíveis, exceto tabulação e quebra de linha.
Resultados negativos são válidos; operandos negativos na expressão de entrada não são.
O arredondamento preserva o comportamento da Sprint 3: metade é arredondada para longe de zero.
Exemplos: `1/8` vira `0.13`; `-1/8` vira `-0.13`; `1999/1000` vira `2.00`.

No Python, a carga do armazenamento valida a expressão com AST e confere os resultados.
No navegador, `validarHistorico.mjs` confere tipos, campos, datas, IDs, gramática e a
coerência entre a fração e sua formatação usando BigInt. **Não reavalia a expressão**;
portanto, não atesta que um JSON de terceiros contém resultados matematicamente corretos.
Renderize todas as strings como texto React; nunca use `eval`, `Function` ou HTML bruto.
JSON com chaves duplicadas é rejeitado no armazenamento Python; o `JSON.parse` do
navegador mantém a última ocorrência. O exportador Python sempre produz chaves únicas.

A exportação inclui todos os registros visíveis, inclusive temporários, por ação explícita.
Isso não altera a preferência de persistência. Não exporta imagens, credenciais,
configurações, caminhos de arquivos ou flags internas.

`historico_exemplo.json` contém **dados ilustrativos**, inclusive a explicação escrita
para demonstração. Não é evidência de OCR, uso real ou chamada Gemini e nunca é
carregado automaticamente pelo aplicativo.

Comprimento de texto é contado como `len(str)` em Python e `Array.from(texto).length`
em JavaScript, nunca em bytes ou unidades UTF-16. Surrogates isolados são inválidos.
Rejeitam-se U+0000–U+001F (exceto U+0009 e U+000A) e U+007F. Texto vazio ou
composto somente pelos espaços reconhecidos por `str.strip()` é inválido:
U+0009–U+000D, U+001C–U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A,
U+2028, U+2029, U+202F, U+205F e U+3000.
Datas: ano 0001–9999, mês 01–12, dia conforme calendário gregoriano/bissextos,
hora 00–23, minuto/segundo 00–59; fuso com hora 00–23 e minuto 00–59.
Não se aceitam segundos intercalares, ano zero, espaços ou fuso ausente.
Inteiros canônicos não têm `+`, zeros à esquerda ou `-0`; frações são irredutíveis
com denominador maior que 1. Zero é `0`, nunca `0/1`. Arredondamento negativo
que resulta em zero é mostrado como `0.00`, sem sinal negativo.
