# O que veio do LIC (Radar Licita+) e como foi usado

| Arquivo no sonar-automais | Origem no LIC | Como |
|---|---|---|
| `backend/sonar/pncp.py` | `licitamais/pncp.py` | cópia fiel (cliente com repetição, 204/429/5xx) |
| `backend/sonar/db.py` | `licitamais/db.py` | cópia (pool, disjuntor de 15 s, IAM no RDS) |
| `backend/sonar/config.py` | `licitamais/config.py` | adaptado (UFS_REGRAS, PARCEIRO, FIPE) |
| `backend/sonar/eventos.py` | `licitamais/eventos.py` | adaptado: limite de placas FIPE/dia; placa repetida não conta; contador da placa |
| `backend/sonar/visitantes.py` | `licitamais/visitantes.py` | adaptado: cookie + impressão + teto por IP |
| `backend/sonar/planos.py` | `licitamais/planos.py` | mesmo padrão (fonte única dos números), planos do CAR |
| `backend/sonar/alertas.py` | `licitamais/alertas.py` | monitoramento de placa |
| `backend/migracoes/001_inicial.sql` | `001`, `002` | usuário, visitante, uso_diario do LIC + tabelas do CAR |
| `infra/` | `infra/` | cópia das pilhas CDK, a renomear (ver `infra/LEIA-ME.md`) |
| `infra/github-workflows/` (testes.yml e deploy.yml; mover para `.github/workflows/` ao criar o repositório) | `.github/workflows/` | testes adaptados; deploy como referência |
| `backend/Dockerfile`, `docker-compose.yml`, `.gitignore` | raiz/backend | renomeados |

A reaproveitar depois (não copiados ainda): `assinaturas.py` (Asaas), `privacidade.py`, `geo.py`, `fila.py`,
`coletas.py` (fila por plano), `web/` (React + Vite + PWA + Cognito), `coleta/semear.py` (modo demonstração).
