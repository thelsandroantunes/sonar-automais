# API (modo demonstração)

Base: `http://localhost:8000` · documentação interativa: `/docs` · protótipo: `/demo/`

Todos os dados vêm de `dados-referencia/ficticios/`. O plano vem na URL só na demonstração; em produção vem do login.

| Método e rota | O que faz | Plano mínimo |
|---|---|---|
| `GET /saude` | situação da API | — |
| `GET /planos` | planos, preços e itens liberados (fonte: `sonar/planos.py`) | — |
| `GET /placa/{placa}/fipe?plano=` | FIPE grátis + contador “consultada N vezes”; limite de placas/dia (visitante 10, grátis 30; repetida não conta) | Visitante |
| `GET /placa/{placa}/laudo?plano=&preco_pedido=` | laudo: nota 0–100, veredito, itens por fonte, débitos, valor justo e oferta | Essencial / Completa |
| `GET /modelos` | FIPE por modelo, sem placa | Visitante |
| `GET /minha-placa/{placa}/avisos?anos_sem_multa=` | vigiar a placa: multa no Diário Oficial (prazo de defesa), IPVA, licenciamento, recall, Zona Franca | Grátis |
| `GET /leiloes?plano=&uf=` | radar de leilões públicos (Grátis 24 h depois; Pro na hora) | Grátis |
| `GET /vender/quanto-pedir?placa=&estado=` | preço sugerido para vender (ótimo / bom / regular) | Completa |
| `GET /comprar/transferencia?despachante=` | custo da transferência no Detran-AM | Grátis |
| `GET /comprar/custo-mensal/{placa}` | custo de ter o veículo por mês | Grátis |
| `GET /parceiros` | parceiros por comissão | — |
| `GET /revenda/painel` | painel do estoque da revenda (nota e situação por placa) | Pro |

Exemplos: `/placa/OAB7C89/laudo?plano=completa&preco_pedido=118000` (crítico, Zona Franca, leilão) ·
`/placa/PHX4E56/laudo?plano=essencial` (atenção) · `/placa/QZA1B23/laudo` (sem pendências) · `/placa/QZB2E34/laudo` (moto,
leilão público).
