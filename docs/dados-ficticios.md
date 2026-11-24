# Dados fictícios

Tudo em `dados-referencia/ficticios/` é inventado para demonstração e testes. Não usar como informação real.

| Arquivo | Conteúdo |
|---|---|
| `veiculos.json` | 6 veículos: QZA1B23 (sem pendências), PHX4E56 (atenção), OAB7C89 (crítico + Zona Franca), QZB2E34 (moto vendida em leilão público), RTM3C21 e PXA9F87 (estoque da revenda). Cadastro, FIPE de 12 meses, débitos e o que o parceiro responderia |
| `multas_diario_manaus.json` | 8 multas no formato dos editais da IMMU (placa, auto, código, valor, publicação, prazo de defesa) |
| `leiloes_publicos.json` | 5 lotes (Detran-AM, PRF, prefeitura via PNCP). A data do 5º leilão do Detran-AM (27/11/2026) é real; o resto é inventado |
| `taxas_detran_am.json` | taxas da transferência, vencimento do licenciamento por final de placa e do IPVA |
| `estoque_revenda.json` | revenda fictícia com 6 placas |
| `parceiros_comissao.json` | parceiros por comissão e percentuais de referência |

`dados-referencia/exemplos/` tem textos de edital (IMMU e resenha de leilão do Detran-AM) para testar os leitores de PDF
(`sonar/fontes/editais_pdf.py`).

Qualquer placa válida que não esteja nos arquivos abre um dos 4 cenários principais (escolha fixa pela placa), para a
demonstração sempre mostrar uma tela completa. Para trocar por dados reais: `PARCEIRO=<fornecedor>` no `.env` e as coletas
da Fase 1 gravando em `registro_publico`.
