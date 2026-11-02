import { useRef, useState } from "react";
import { lerArquivoHistorico } from "./validarHistorico.mjs";

export default function HistoricoJovi() {
  const [registros, setRegistros] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const leituraAtual = useRef(0);

  async function selecionar(evento) {
    const arquivo = evento.target.files?.[0];
    const leitura = ++leituraAtual.current;
    setRegistros(null);
    setErro("");
    if (!arquivo) {
      setCarregando(false);
      return;
    }
    setCarregando(true);
    try {
      const novos = await lerArquivoHistorico(arquivo);
      if (leitura === leituraAtual.current) setRegistros(novos);
    } catch (falha) {
      if (leitura === leituraAtual.current) {
        setErro(falha instanceof Error ? falha.message : "Não foi possível ler o arquivo.");
      }
    } finally {
      if (leitura === leituraAtual.current) setCarregando(false);
    }
  }

  return (
    <section aria-label="Histórico do JOVI MATH" className="historico-jovi">
      <h2>Importar histórico do JOVI MATH</h2>
      <p>Selecione o JSON exportado pelo programa Python. A leitura ocorre neste navegador.</p>
      <label>
        Arquivo JSON
        <input type="file" accept=".json,application/json" onChange={selecionar} />
      </label>
      <div aria-live="polite">
        {carregando && <p>Lendo arquivo...</p>}
        {erro && <p role="alert">{erro}</p>}
        {!carregando && !erro && registros === null && <p>Nenhum arquivo selecionado.</p>}
        {registros?.length === 0 && <p>O arquivo é válido e o histórico está vazio.</p>}
      </div>
      {registros?.length > 0 && (
        <ul>
          {registros.map((registro) => (
            <li key={registro.id}>
              <p><strong>{registro.expressao} = {registro.resultado_formatado}</strong></p>
              <p>Resultado exato: {registro.resultado_exato}</p>
              <p>Origem: {registro.origem === "camera" ? "câmera" : registro.origem}</p>
              <time dateTime={registro.data_hora}>
                {new Date(registro.data_hora).toLocaleString("pt-BR")}
              </time>
              {registro.explicacao === null ? (
                <p>Sem explicação gerada.</p>
              ) : (
                <p style={{ whiteSpace: "pre-wrap" }}>
                  Explicação gerada por IA (pode conter erros):{"\n"}{registro.explicacao}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
