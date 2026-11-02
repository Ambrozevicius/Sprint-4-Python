// Valida o contrato para exibição. Não executa nem recalcula a expressão.
export const MAX_BYTES = 5 * 1024 * 1024;

function exigir(condicao, mensagem) {
  if (!condicao) throw new Error(mensagem);
}

function objeto(valor, campos) {
  return valor !== null && typeof valor === "object" && !Array.isArray(valor)
    && Object.keys(valor).length === campos.length
    && campos.every((campo) => Object.hasOwn(valor, campo));
}

function texto(valor, limite) {
  // Mesmos espaços de str.strip() e pontos de código de len(str) no Python.
  return typeof valor === "string"
    && valor.replace(/[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/gu, "").length > 0
    && Array.from(valor).length <= limite
    && !/[\u0000-\u0008\u000b-\u001f\u007f\ud800-\udfff]/u.test(valor);
}

function dataValida(valor) {
  if (typeof valor !== "string" || valor.length > 40) return false;
  const partes = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|([+-])(\d{2}):(\d{2}))$/u.exec(valor);
  if (!partes) return false;
  const [, ano, mes, dia, hora, minuto, segundo, fuso, , horaFuso, minutoFuso] = partes;
  const a = Number(ano), m = Number(mes), d = Number(dia);
  const bissexto = a % 4 === 0 && (a % 100 !== 0 || a % 400 === 0);
  const dias = [31, bissexto ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return a >= 1 && m >= 1 && m <= 12 && d >= 1 && d <= dias[m - 1]
    && Number(hora) < 24 && Number(minuto) < 60 && Number(segundo) < 60
    && (fuso === "Z" || (Number(horaFuso) < 24 && Number(minutoFuso) < 60))
    && !Number.isNaN(Date.parse(valor));
}

function expressaoValida(valor) {
  if (!texto(valor, 200) || !/^[0-9()+*/-]+$/u.test(valor) || !/[+*/-]/u.test(valor)) return false;
  // Confere somente a gramática: número ou '(' quando se espera um operando.
  const partes = valor.match(/\d+|[()+*/-]/gu);
  let esperaOperando = true, abertos = 0;
  for (const parte of partes) {
    if (/^\d+$/u.test(parte)) {
      if (!esperaOperando || (parte.length > 1 && parte[0] === "0")) return false;
      esperaOperando = false;
    } else if (parte === "(") {
      if (!esperaOperando) return false;
      abertos += 1;
    } else if (parte === ")") {
      if (esperaOperando || abertos === 0) return false;
      abertos -= 1;
    } else {
      if (esperaOperando) return false;
      esperaOperando = true;
    }
  }
  return !esperaOperando && abertos === 0;
}

function mdc(a, b) {
  while (b !== 0n) [a, b] = [b, a % b];
  return a;
}

function formatarExato(valor) {
  exigir(texto(valor, 512) && /^(?:0|-?[1-9]\d*)(?:\/[1-9]\d*)?$/u.test(valor),
    "Resultado exato inválido.");
  const [numerador, denominador = "1"] = valor.split("/");
  let n = BigInt(numerador), d = BigInt(denominador);
  const negativo = n < 0n;
  n = negativo ? -n : n;
  exigir(mdc(n, d) === 1n && !(valor.includes("/") && d === 1n),
    "Resultado exato deve estar simplificado.");
  if (d === 1n) return numerador;
  let centavos = n * 100n / d;
  if ((n * 100n % d) * 2n >= d) centavos += 1n;
  return `${negativo && centavos !== 0n ? "-" : ""}${centavos / 100n}.${String(centavos % 100n).padStart(2, "0")}`;
}

export function validarHistorico(dados) {
  exigir(objeto(dados, ["versao_schema", "projeto", "exportado_em", "registros"]),
    "Estrutura do arquivo inválida.");
  exigir(dados.versao_schema === 1,
    "Versão de esquema desconhecida. Esperado: 1.");
  exigir(dados.projeto === "JOVI MATH", "Projeto desconhecido.");
  exigir(dataValida(dados.exportado_em), "Data de exportação inválida ou sem fuso.");
  exigir(Array.isArray(dados.registros) && dados.registros.length <= 1000,
    "Registros deve ser uma lista com até 1000 itens.");
  const ids = new Set();
  for (const registro of dados.registros) {
    exigir(objeto(registro, ["id", "expressao", "resultado_exato", "resultado_formatado",
      "origem", "data_hora", "explicacao"]), "Registro com campos inválidos.");
    exigir(texto(registro.id, 80) && /^[A-Za-z0-9_-]+$/u.test(registro.id)
      && !ids.has(registro.id), "ID inválido ou duplicado.");
    ids.add(registro.id);
    exigir(expressaoValida(registro.expressao), "Expressão fora do formato permitido.");
    exigir(texto(registro.resultado_formatado, 512)
      && registro.resultado_formatado === formatarExato(registro.resultado_exato),
    "Resultado formatado inconsistente com a fração informada.");
    exigir(["camera", "imagem", "digitado"].includes(registro.origem), "Origem desconhecida.");
    exigir(dataValida(registro.data_hora), "Data do registro inválida ou sem fuso.");
    exigir(registro.explicacao === null || texto(registro.explicacao, 2000),
      "Explicação deve ser texto ou null.");
  }
  return dados.registros;
}

export async function lerArquivoHistorico(arquivo) {
  exigir(arquivo && arquivo.size <= MAX_BYTES, "Selecione um JSON de até 5 MiB.");
  const bytes = await arquivo.arrayBuffer();
  let conteudo;
  try {
    conteudo = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    throw new Error("O arquivo deve usar codificação UTF-8 válida.");
  }
  let dados;
  try {
    dados = JSON.parse(conteudo);
  } catch {
    throw new Error("O arquivo não contém JSON válido.");
  }
  return validarHistorico(dados);
}
