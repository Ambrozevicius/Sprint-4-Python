# Integração manual com a equipe Web

**Implementado:** exportação no Python e componente React de referência.
**Pendente:** incorporar e testar o componente na página real da equipe Web.
Nenhum repositório remoto foi modificado.

1. Copie `HistoricoJovi.jsx` e `validarHistorico.mjs` juntos para uma pasta em `src/`
   no projeto React existente.
2. Importe e inclua o componente em uma seção apropriada da página:

   ```jsx
   import HistoricoJovi from "./components/HistoricoJovi.jsx";

   // Dentro do JSX da página existente:
   <HistoricoJovi />
   ```

3. Aplique as classes e estilos do site à seção `historico-jovi`, sem reconstruir a página.
4. Inicie o projeto com os comandos já usados pelo repositório.
5. No Python, faça cálculos e escolha **11 — Exportar histórico JSON**.
6. No seletor do componente, escolha o arquivo indicado em `exportacoes/`.
   Ele também funciona com o Python fechado.

O componente completo está em [HistoricoJovi.jsx](HistoricoJovi.jsx); a validação está em
[validarHistorico.mjs](validarHistorico.mjs). Não exige novas dependências além de React
e um navegador moderno com BigInt, TextDecoder e File.arrayBuffer.
O leitor limita o arquivo antes de decodificá-lo, valida o contrato e evita que uma
leitura antiga substitua uma seleção mais recente.

Estados implementados: nenhum arquivo, lendo, histórico vazio, erro e lista de registros.
Exibe expressão, resultado pronto, resultado exato, origem, data local do navegador e
explicação rotulada como IA. `null` é apresentado como ausência de explicação.
O resultado calculado no Python é o oficial.

Teste `historico_exemplo.json` primeiro: é **inteiramente ilustrativo**. Depois teste
uma exportação real e um histórico vazio. Tente JSON quebrado, versão 2, ID duplicado,
origem desconhecida, data impossível, tipo incorreto e arquivo maior que 5 MiB.
Confirme que textos como `<script>` em uma explicação aparecem apenas como texto.

Não use chave Gemini no frontend, `eval`, `new Function`, `dangerouslySetInnerHTML`,
backend, upload, acesso direto ao disco ou execução de Python no navegador.
O nome da função é **Importar histórico do JOVI MATH**, não “Teste agora”.

A montagem, a aparência e a integração no site devem ser verificadas no repositório React.
Os testes de manutenção Python/Node ficam fora desta entrega técnica.
