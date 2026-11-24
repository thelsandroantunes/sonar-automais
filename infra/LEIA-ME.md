# Infra (AWS CDK) — vinda do Radar Licita+

Cópia das pilhas CDK do LIC (já implantadas e testadas lá), com os nomes trocados para Sonar:
`SonarAcessoGitHub` (OIDC), `SonarRede` (VPC sem NAT), `SonarBanco` (RDS PostgreSQL 16), `SonarDominio`
(Route 53, sonarautomais.com.br), `SonarTarefas` (Fargate com agenda), `SonarApi` (Cognito + API Gateway + Lambda),
`SonarSite` (Amplify), `SonarMonitoramento` (alarmes) e `SonarEmail` (SES).

`cdk.json` sem dados do LIC (sem e-mails, conta ou zona DNS): preencher na Fase 1.

## A adaptar na Fase 1
1. `sonar_infra/tarefas.py`: trocar a agenda do PNCP/licitações por: leilões PNCP (diária), editais do Detran-AM
   (semanal), Diário Oficial de Manaus/IMMU (diária), FIPE (mensal). Repositório ECR `sonar-automais/tarefas`.
2. `sonar_infra/api.py`: rotas da `backend/api/main.py`; a Lambda "borda" chama o parceiro pago e a FIPE.
3. Região de produção `sa-east-1` (também necessária para o DJEN/CNJ, que bloqueia acesso de fora do Brasil).
4. `github-workflows/`: mover `testes.yml` e `deploy.yml` para `.github/workflows/` (a pasta `.github` não pôde ser
   gravada pelas ferramentas remotas).
