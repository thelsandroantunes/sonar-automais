# Pesquisa de mercado — consulta veicular por placa (20/11/2026)

## Demanda
- Usados: 18,5 milhões de transferências em 2025 (≈7 usados por 0 km); o setor projeta ~20 milhões em 2026 — Alvesp/Sindiauto, Estadão Blue Studio.
- Novos: 5.124.544 emplacamentos em 2025 (Fenabrave). Financiamentos: 7,3 milhões de veículos em 2025 — base do gravame.
- Compra de usado é decisão cara e rara: o comprador paga uma vez por segurança. Revendas, despachantes e financeiras consultam todo dia (B2B recorrente).

## Concorrência e preços (varejo, out–nov/2026)
| Serviço | Produto | Preço |
|---|---|---|
| Olho no Carro | Débitos nacionais e estaduais | R$ 13,90 |
| Olho no Carro | Leilão + dados | R$ 34,90 (promo) |
| ZapCar | Simples / Completa | R$ 5,98 / R$ 36,00 |
| ZapCar (itens) | Roubo/furto · Gravame · RENAJUD · Débitos · Leilão · Monitoramento | R$ 5,99 · 6,99 · 6,99 · 6,99–9,99 · 19,99 · 14,99/mês |
| AnyCar | Completa B2C / B2B (API inclusa, sem franquia) | R$ 59,90 / R$ 39,99 |
| Infoconferi | Completa | R$ 39,90 |
| Consultar Leilão | Leilão / + fotos / Dossiê | R$ 18,90 / 34,90 / 49,90 |
| Faixas (25 serviços) | Leilão simples · com fotos · completa | R$ 10–39,90 · 34,90–49,90 · 38,99–79,90 |

Não foi encontrada fonte gratuita de histórico de leilão por placa. O mercado é lotado e indiferenciado: quase todos entregam “consta / não consta” em PDF.

## Fontes de dados e APIs
| Fonte | Tipo | Entrada | Cobre | Preço publicado |
|---|---|---|---|---|
| Parallelum FIPE API | pública, grátis (testada, responde) | marca/modelo/ano | valor FIPE | R$ 0 |
| BrasilAPI FIPE | pública, grátis | código FIPE | valor FIPE | R$ 0 (fora do ar no teste de 20/11) |
| APIBrasil — FIPE por Placa | agregador | placa | código FIPE, modelo, histórico, IPVA estimado, chassi | R$ 0,06 |
| APIBrasil — Relatório 360, Leilão (várias) | agregador | placa | cadastro, débitos, roubo/furto, gravame, leilão, recall | sob consulta (CNPJ) |
| AnyCar — APIs avulsas | agregador | placa | leilão, sinistro, FIPE, gravame, dados básicos + 40 tipos | completa R$ 39,99; avulsas sob consulta |
| Consultar Placa — API | agregador | placa/chassi | Detran, RENAINF, roubo/furto, leilão, PT, RENAJUD, FIPE, recall | sob consulta |
| ZapCar — API | agregador | placa | itens avulsos | catálogo de integrações |
| Infosimples — DETRAN/UF, Restrições unificada | RPA/API | placa + RENAVAM (+chassi) | multas, IPVA, licenciamento, restrições (ex.: Detran-AM) | R$ 0,22 → R$ 0,06 por volume + adicionais; franquia R$ 100/mês; R$ 100 de crédito de teste |
| Celcoin / Zapay — Débito veicular | fintech | placa + RENAVAM | IPVA, licenciamento, multas, com pagamento/parcelamento | consulta B2B; receita no pagamento |
| Serpro — Consulta Online Senatran | oficial | placa/RENAVAM/chassi | RENAVAM, RENAINF, RENAJUD, roubo/furto | tabela por portaria (faixas progressivas) |
| Vistoria cautelar | privado (ECVs) | placa | laudos anteriores | sem API pública; poucos (ex.: Concar) mostram histórico |

### Achados
1. **Só a FIPE é pública e gratuita.** O resto vem de RENAVAM/RENAINF (Senatran) ou de bases privadas.
2. **Acesso direto à Senatran é caro em tempo:** Portaria Senatran 139/2025 exige CNPJ, e-CNPJ, responsável técnico, maturidade em segurança (nota ≥ 4 ou ISO 27001), contrato com o Serpro **e** com uma GCC (gerenciadora de consentimento), análise de até 60 dias úteis. Dados de proprietário são restritos. → Fase 4.
3. **Infosimples desativou a API SENATRAN/Veículo** (dependia de login gov.br, 5 consultas/dia). Não contar com RPA em portal gov.br.
4. **Débitos (IPVA e multas) exigem RENAVAM** → o fluxo precisa primeiro de uma consulta de dados básicos pela placa.
5. **Busca e apreensão não tem base pública por placa.** Agregadores entregam RENAJUD (restrição judicial) e indícios de bases de financeiras. Mostrar como alerta, nunca como certeza.
6. **Vistoria cautelar** não tem fonte ampla: tratar por parceria com rede de vistoria (ECV).

## Conclusões
1. MVP via **agregador por API** (cotar 3 na Fase 0 com 20 placas reais do AM) + FIPE grátis + débitos via Celcoin/Zapay/Infosimples.
2. Diferencial: **parecer explicado** (nota 0–100, “pode comprar / negocie / não compre”), **débitos pagáveis no app** e **foco regional (AM) + revendas**, repetindo a estratégia do Radar Licita+.
3. Preço alvo da completa R$ 39,90 (dentro da faixa). Meta de custo ≤ R$ 15 por completa; com o custo de referência atual (≈R$ 21) a margem bruta fica em ~42%.
4. LGPD: não exibir nome/CPF do proprietário.

## Fontes
- zapcarconsulta.com.br/precos (tabela de preços) · consultarleilao.com.br/blog/quanto-custa-consultar-leilao-pela-placa (25 serviços, out/2026)
- anycar.com.br/para-empresas e /para-empresas/api · apibrasil.io/precos · docs.consultarplaca.com.br
- infosimples.com/consultas/precos, /detran-am-veiculo, /senatran-veiculo
- centraldeajuda.serpro.gov.br/consultasenatran (preços, classificação, FAQ da Portaria 139/2025)
- developers.celcoin.com.br (Débito veicular) · usezapay.com.br
- parallelum.com.br/fipe/api/v1 · brasilapi.com.br/api/fipe
- Fenabrave, Balcão Automotivo (jan/2026), Alvesp (jan/2026), CNN Brasil (jan/2026)
