# Sonar Auto+ — Plano estratégico (24/11/2026)

**Produto:** consulta veicular pela placa para o Brasil, **começando pelo Amazonas com as regras do Amazonas**. Cada novo
estado entra como um “pacote de regras da UF” (IPVA, restrições, multas da capital, leilões locais), sem mudar o núcleo.

**Frase de posicionamento:** “A consulta que entende as regras do seu estado — e mostra em números e cores se vale comprar.”

---

## 1. Princípios
1. **Público primeiro, parceiro só onde não há dado aberto.** Cada fonte pública que entra na base derruba o custo do laudo.
2. **Uma regra por estado, um núcleo para o Brasil.** O laudo é igual em todo o país; o que muda por UF fica em `regras/<uf>.py`.
3. **Visual antes de texto.** Nota 0–100 com semáforo, “quanto vale de verdade”, “quanto oferecer” e gráficos que se explicam.
4. **Mesma base técnica do Radar Licita+ (LIC).** Reaproveitar infraestrutura, limites por plano, visitante, alertas, coleta
   com fila e o cliente do PNCP (ver seção 6).
5. **LGPD:** nunca mostrar nome/CPF do proprietário; placa guardada com hash nos registros de uso.

## 2. Ondas de expansão
| Onda | Quando (ref.) | Estados | Regras novas da onda |
|---|---|---|---|
| 0 — Validação | dez/2026 | AM | cotação de parceiros, 20 placas reais, preço |
| 1 — Amazonas | jan–mar/2027 | AM | restrição tributária ZFM, IPVA AM 2026 (alíquota reduzida, bom condutor, 3x), multas IMMU publicadas no Diário Oficial de Manaus, leilões e resenhas do Detran-AM |
| 2 — Norte | abr–jun/2027 | RR, AP, AC, RO, PA, TO | áreas de livre comércio (Boa Vista, Macapá/Santana, Brasiléia/Cruzeiro do Sul, Guajará-Mirim) usam a mesma lógica da ZFM; IPVA e leilões de cada Detran |
| 3 — Grandes mercados | 2º sem/2027 | SP, MG, RJ, PR, RS, BA, GO, DF | IPVA de cada UF, multas das capitais, leilões estaduais |
| 4 — Brasil | 2028 | demais UFs | pacote mínimo: IPVA + leilões + multas da capital |

Antes da sua onda, o estado já é atendido com o **laudo nacional** (parceiros + fontes públicas nacionais), sem as regras locais.

## 3. Base própria com dados públicos
| Fonte | Como lê | Frequência | Vira no laudo | Situação |
|---|---|---|---|---|
| Tabela FIPE (Parallelum; BrasilAPI reserva) | API pública grátis | mensal | valor e histórico 12 meses | validada |
| PNCP — leilões (modalidades 1 e 13) | API pública (mesmo cliente do LIC) | diária | “vendido em leilão público”, com órgão, lote e data | validada (24/11/2026): 172 leilões publicados no Brasil de 1 a 24/11; 42 de veículos; 18 placas já no texto do objeto (os itens trazem mais). No AM, nenhum leilão de veículo no PNCP no período → no AM os editais do Detran-AM pesam mais |
| Detran-AM — editais de leilão e resenhas de notificação | PDF no site do Detran-AM | semanal | “veículo em pátio / anunciado em leilão” | validada (5 leilões em 2026); leitura de PDF a construir |
| IMMU Manaus — editais de notificação de autuação (Diário Oficial do Município) | PDF público com placa, auto e data | diária | multas municipais publicadas por edital (quando a carta não chegou) | validada (PDFs públicos); leitura a construir |
| Diário Oficial do AM e dos Municípios (AAM) | PDF / texto | diária | leilões e notificações do interior | a validar |
| Querido Diário (Open Knowledge Brasil) | API pública | diária | diários municipais pesquisáveis por placa | a validar cobertura do AM |
| DJEN / Comunica (CNJ) | API pública por texto | diária | indício de busca e apreensão citado em intimação | a validar (bloqueia acesso de fora do Brasil; testar da AWS sa-east-1) |
| Datajud (CNJ, chave pública) | API pública | mensal | indicador: ações de busca e apreensão por tribunal (não por placa) | a validar |
| Sefaz-AM — regras do IPVA | página/lei | anual | simulador de IPVA | validada |
| Senatran — frota (dados abertos) | planilha | mensal | indicadores do mercado por município | validada |
| PRF e Receita Federal — leilões | sites públicos | semanal | leilões federais de veículos | a validar |
| Recall (Senacon / montadoras) | listas públicas | mensal | recall por modelo/ano | a validar |
| **Própria** | nossos registros | contínua | contador “placa consultada N vezes”, histórico de laudos | — |

**Continua com parceiro (não existe aberto):** roubo/furto, gravame, RENAJUD, leilão de seguradoras/bancos, débitos do Detran por
placa (Celcoin, Zapay ou Infosimples), multas federais RENAINF.

**Efeito no custo (referência, ver aba Decisão do protótipo):** laudo completo só com parceiros ≈ R$ 23,60 → com a base
pública (leilão público, multas publicadas em diário) ≈ R$ 21,40 → com desconto de volume do parceiro (−30%)
≈ R$ 15 (meta ≤ R$ 15); margem bruta na Completa ≈ 51% após taxa de pagamento e impostos. O item mais caro é o leilão de seguradoras/bancos (≈ R$ 10), que não existe aberto.

## 4. Planos — o que cada um pode fazer
| Recurso | Visitante | Grátis | Essencial | Completa | Pro (revenda) | Empresa / API |
|---|---|---|---|---|---|---|
| Preço (ref.) | R$ 0 | R$ 0 | R$ 19,90 por placa | R$ 39,90 por placa (moto R$ 24,90) | R$ 199/mês | R$ 599/mês |
| Placas FIPE por dia | 10 | 30 | — | — | ilimitado | ilimitado |
| Valor FIPE + gráfico 12 meses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Contador “placa consultada N vezes” | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Simulador de IPVA (regras da UF) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Checklist antigolpe | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| “N pontos de atenção” | bloqueado | bloqueado | ✓ | ✓ | ✓ | ✓ |
| Roubo/furto, gravame ativo/baixado, RENAJUD | — | — | ✓ | ✓ | ✓ | ✓ |
| IPVA, licenciamento, multas municipais e estaduais | — | — | ✓ | ✓ | ✓ | ✓ |
| Restrição tributária ZFM/ALC | — | — | ✓ | ✓ | ✓ | ✓ |
| Leilão público (base própria) | — | — | ✓ | ✓ | ✓ | ✓ |
| Leilão de seguradoras/bancos, com fotos | — | — | — | ✓ | ✓ | ✓ |
| Indício de busca e apreensão, multas federais, recall | — | — | — | ✓ | ✓ | ✓ |
| Nota 0–100, “quanto vale de verdade” e “quanto oferecer” | — | — | nota | ✓ | ✓ | ✓ |
| Link/PDF compartilhável (“vendedor verificado”) | — | — | — | ✓ | ✓ | ✓ marca própria |
| Monitorar a placa (nova multa, gravame baixado, restrição) | — | — | — | 30 dias | 50 placas | 300 placas |
| Laudos completos inclusos | — | — | — | — | 10/mês (+R$ 24,90) | 40/mês (+R$ 19,90) |
| Painel do estoque, consulta em lote, usuários | — | — | — | — | ✓ (3 usuários) | ✓ (ilimitado) + API |
| Pagar/parcelar débitos no app | — | — | ✓ | ✓ | ✓ | ✓ |
| Atendimento | — | — | WhatsApp | WhatsApp | WhatsApp prioritário | gerente de conta |

Pacote “Procurando carro”: 3 completas por R$ 99. Débitos pagos pelo app geram comissão do parceiro.

## 5. Visual e indicadores (para quem não entende indicadores)
- **Nota 0–100 em semáforo** (verde ≥ 80 “pode seguir”, amarelo 50–79 “negocie”, vermelho < 50 “não compre”).
- **“Quanto vale de verdade”:** escada FIPE → desconto por leilão → débitos → valor justo.
- **“Quanto oferecer”:** barra comparando preço pedido, valor justo e oferta sugerida, com a economia em R$.
- **Débitos em rosca** (IPVA, multas municipais, estaduais, federais) com total em destaque.
- **FIPE 12 meses em linha** com a variação em %.
- **Selos** curtos: “ZFM: não sai do AM sem pagar imposto”, “muito procurada”, “multa publicada no Diário Oficial”.
- **Painel da revenda:** placas do estoque por situação, alertas por tipo, valor do estoque e “prejuízo evitado”.

## 6. O que reaproveitar do LIC (Radar Licita+)
| LIC | Uso no CAR |
|---|---|
| `licitamais/planos.py` (fonte única dos limites) | `sonar/planos.py`: limites de FIPE/dia, itens por plano, monitoramento |
| `visitantes.py` + `eventos.py` (cookie + impressão + teto por IP, uso diário) | uso justo da FIPE grátis e antiabuso |
| `db.py` (pool, disjuntor de 15 s, IAM no RDS) e `config.py` | iguais, renomeados |
| `pncp.py` (cliente com repetição e tratamento de erros do PNCP) | coleta de leilões públicos (modalidades 1 e 13) |
| `coletas.py` (coleta por UF sob demanda, fila por plano) | coleta das fontes por UF na ordem das ondas |
| `alertas.py` | monitoramento de placa (nova multa, gravame baixado, leilão) |
| `assinaturas.py` (Asaas), `privacidade.py`, `geo.py` | pagamento por Pix/cartão, anonimização, região aproximada |
| `infra/` (CDK: OIDC, rede sem NAT, RDS, Fargate com agenda, Cognito + API Gateway + Lambda, Amplify, SES, alarmes) | mesma arquitetura, pilhas `Sonar*` |
| `.github/workflows` (testes, deploy, imagem) | iguais |
| `coleta/semear.py` e modo demonstração | placas fictícias para testar telas sem banco |

## 7. Metas (primeiros 6 meses no AM)
| Indicador | Meta |
|---|---|
| Consultas FIPE grátis/mês | 30 mil |
| Conversão grátis → laudo pago | 3–5% |
| Laudos pagos/mês | 1.000 |
| Revendas e despachantes no Pro | 25 |
| Custo médio do laudo completo | ≤ R$ 15 |
| Margem bruta do laudo completo | ≥ 50% (estimativa atual ≈ 51%) |

## 8. Riscos
- **Parceiros caros** → base pública cobre mais itens a cada onda; fornecedor reserva por item.
- **Leitura de PDF de diário oficial muda de formato** → testes com PDFs reais guardados em `04-dados/`; alerta quando a leitura cai.
- **LGPD em dados judiciais** → mostrar só “indício” e a fonte; nada de nome de parte.
- **Concorrência por preço** → competir por regra local + visual + WhatsApp, não por R$ 5,98.

## 9. Serviços além da placa (24/11/2026) — teste com o menor custo possível
Decisão do dono: testar com o menor custo operacional possível. Filtro: primeiro o que roda com dado público e automação ou
que paga comissão sem custo de dado; parceiro pago só quando alguém compra o laudo.

| Grupo | Serviços (recomendação) |
|---|---|
| Formas de entrada | FIPE por modelo sem placa (MVP); chassi/RENAVAM/motor, QR do CRLV-e, conferir anúncio colado pelo usuário (depois) |
| Para o dono do veículo | vigiar a minha placa — multas no Diário Oficial, IPVA, licenciamento (MVP, 1 placa no Grátis); calendário do IPVA (MVP); passo a passo da Zona Franca (MVP); modelo de defesa de multa com o prazo do edital, R$ 9,90 (depois) |
| Para quem vende | “quanto pedir” (MVP, Completa); modelo de contrato + lembrete de comunicar a venda (MVP, Grátis) |
| Para quem compra | custo da transferência no Detran-AM (MVP); custo de ter o carro e comparador por orçamento (depois) |
| Radar de leilões | leilões públicos do Detran-AM, PNCP e prefeituras — Grátis com 24 h de atraso, Pro na hora (MVP; código do LIC) |
| Por comissão | pagar/parcelar débitos (MVP); vistoria cautelar, despachante, seguro, financiamento (depois) |
| Para empresas | painel do estoque, avaliação de troca, frotas, laudo com a marca do despachante (depois do teste) |

**Ordem do teste:** 1) FIPE grátis + vigiar a placa + calendário do IPVA · 2) radar de leilões · 3) pagar débitos + vistoria
(comissão) · 4) laudo Essencial/Completa (único custo de parceiro, só quando alguém paga) · 5) vendedor verificado, quanto
pedir, contrato · 6) revendas e frotas.

Evitar: consulta por CPF e dados do proprietário (LGPD e restrição da Senatran). Conferir anúncio só com texto colado pelo
usuário — não ler sites de terceiros.
