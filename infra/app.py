#!/usr/bin/env python3
"""App CDK do Sonar Auto+ (Etapa 2). Pilhas por ordem de implantação:

  SonarAcessoGitHub  – OIDC para o GitHub Actions (1x, pelo CloudShell)
  SonarRede          – VPC sem NAT
  SonarBanco         – RDS PostgreSQL 16
  SonarDominio       – zona DNS do sonarautomais.com.br (Route 53)
  SonarTarefas       – ECR + Fargate: migrações e coleta do PNCP 2x/dia (2.2)
  SonarApi           – Cognito + API Gateway + Lambdas da API e da borda (2.3; implantada pelo workflow api.yml)
  SonarSite          – Amplify Hosting em sonarautomais.com.br + api.sonarautomais.com.br (2.4; deploy.yml)
                       (us-east-1 é bloqueado na conta gratuita: sem CloudFront com domínio próprio)
  SonarMonitoramento – alarmes por e-mail (SNS) + painel do CloudWatch (2.6; deploy.yml)
  SonarEmail         – SES do domínio: DKIM, MAIL FROM, DMARC (2.7; deploy.yml)
"""
import os

import aws_cdk as cdk

from sonar_infra.acesso_github import AcessoGitHub
from sonar_infra.api import Api
from sonar_infra.banco import Banco
from sonar_infra.dominio import Dominio
from sonar_infra.email import Email
from sonar_infra.monitoramento import Monitoramento
from sonar_infra.rede import Rede
from sonar_infra.site import Site
from sonar_infra.tarefas import Tarefas

app = cdk.App()
regiao = app.node.try_get_context("regiao") or "us-east-2"  # conta "AWS (new)": região fixa; sa-east-1 na produção
amb = cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=regiao)

AcessoGitHub(app, "SonarAcessoGitHub", env=amb, repo=app.node.try_get_context("github_repo"),
             repo_ids=app.node.try_get_context("github_repo_ids"))
rede = Rede(app, "SonarRede", env=amb)
banco = Banco(app, "SonarBanco", env=amb, rede=rede)
Dominio(app, "SonarDominio", env=amb, nome=app.node.try_get_context("dominio"))
tarefas = Tarefas(app, "SonarTarefas", env=amb, rede=rede, banco=banco)
dominio = app.node.try_get_context("dominio")
zona_id = app.node.try_get_context("zona_id")
contexto = app.node.try_get_context
Email(app, "SonarEmail", env=amb, dominio=dominio, zona_id=zona_id)
api = Api(app, "SonarApi", env=amb, rede=rede, banco=banco, dominio=dominio, tarefas=tarefas,
          ses_cognito=bool(contexto("ses_cognito")), google=bool(contexto("google_login")),
          asaas=contexto("asaas") or "")
Site(app, "SonarSite", env=amb, dominio=dominio, zona_id=zona_id, api=api)
Monitoramento(app, "SonarMonitoramento", env=amb, api=api, banco=banco, tarefas=tarefas,
              emails=app.node.try_get_context("alertas_emails") or [])

for chave, valor in {"projeto": "sonar-automais", "etapa": "2", "custo": "sonar-automais"}.items():
    cdk.Tags.of(app).add(chave, valor)
app.synth()
