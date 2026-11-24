"""Site em sonarautomais.com.br (sub-etapa 2.4) — plano B, tudo em us-east-2.

A conta gratuita ("AWS (new)") tem uma SCP que nega qualquer ação em us-east-1 (testado em 20/11: o
`cdk bootstrap` de us-east-1 deu AccessDenied). O CloudFront com domínio próprio exige certificado em us-east-1,
então:

  https://sonarautomais.com.br (e www)  → Amplify Hosting (us-east-2). O certificado e a CDN são do próprio
                                              Amplify; o site é enviado como .zip pelo workflow deploy.yml.
  https://api.sonarautomais.com.br      → domínio próprio no API Gateway HTTP (certificado REGIONAL em us-east-2).

Endereços diferentes, mas o mesmo "site" (mesmo domínio registrado): a API libera CORS só para o site, e o cookie
do visitante (`rl_vid`, SameSite=Lax) continua indo junto nas chamadas com `credentials: "include"`.
"""
from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_amplify as amplify
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_iam as iam
from aws_cdk import aws_route53 as r53
from aws_cdk import aws_route53_targets as alvos
from constructs import Construct

from .api import Api

PAPEL_DEPLOY = "sonar-automais-deploy"
RAMO = "main"

# Rotas do React (/painel, /empresas/123…) → index.html; arquivos com extensão conhecida passam direto.
# 23/11/2026: + xml (sitemap.xml devolvia a página do app em vez do mapa do site)
SPA = (r"</^[^.]+$|\.(?!(css|gif|ico|jpg|jpeg|js|png|txt|svg|webp|woff|woff2|ttf|map|json|webmanifest|xml)$)"
       r"([^.]+$)/>")

# 22/11/2026: SAMEORIGIN (era DENY) para o mapa de cliques da administração mostrar a própria página de fundo;
# outros sites continuam sem poder colocar o Sonar dentro de um quadro (frame-ancestors 'self').
CABECALHOS = """customHeaders:
  - pattern: '**'
    headers:
      - key: Strict-Transport-Security
        value: max-age=31536000; includeSubDomains
      - key: X-Content-Type-Options
        value: nosniff
      - key: X-Frame-Options
        value: SAMEORIGIN
      - key: Content-Security-Policy
        value: "frame-ancestors 'self'"
      - key: Referrer-Policy
        value: strict-origin-when-cross-origin
  - pattern: 'index.html'
    headers:
      - key: Cache-Control
        value: no-cache
  - pattern: 'sw.js'
    headers:
      - key: Cache-Control
        value: no-cache
"""


class Site(Stack):
    def __init__(self, escopo: Construct, id_: str, *, dominio: str, zona_id: str, api: Api, **kw) -> None:
        super().__init__(escopo, id_, **kw)
        zona = r53.HostedZone.from_hosted_zone_attributes(self, "Zona", hosted_zone_id=zona_id, zone_name=dominio)

        # ---------------------------------------------------------------- API em api.<domínio>
        host_api = f"api.{dominio}"
        cert_api = acm.Certificate(self, "CertificadoApi", domain_name=host_api,
                                   validation=acm.CertificateValidation.from_dns(zona))
        dominio_api = apigw.DomainName(self, "DominioApi", domain_name=host_api, certificate=cert_api)
        apigw.ApiMapping(self, "MapaApi", api=api.http, domain_name=dominio_api, stage=api.http.default_stage)
        r53.ARecord(self, "AApi", zone=zona, record_name="api", target=r53.RecordTarget.from_alias(
            alvos.ApiGatewayv2DomainProperties(dominio_api.regional_domain_name,
                                               dominio_api.regional_hosted_zone_id)))

        # ---------------------------------------------------------------- site no Amplify Hosting
        self.app = amplify.CfnApp(
            self, "App", name="sonar-automais", platform="WEB",
            description="Sonar Auto+ (site React; enviado como .zip pelo GitHub Actions)",
            custom_rules=[amplify.CfnApp.CustomRuleProperty(source=SPA, target="/index.html", status="200")],
            custom_headers=CABECALHOS)
        ramo = amplify.CfnBranch(self, "Ramo", app_id=self.app.attr_app_id, branch_name=RAMO, stage="PRODUCTION",
                                 enable_auto_build=False, description="publicado pelo workflow deploy.yml")
        dom = amplify.CfnDomain(
            self, "Dominio", app_id=self.app.attr_app_id, domain_name=dominio,
            sub_domain_settings=[amplify.CfnDomain.SubDomainSettingProperty(prefix="", branch_name=RAMO),
                                 amplify.CfnDomain.SubDomainSettingProperty(prefix="www", branch_name=RAMO)],
            enable_auto_sub_domain=False)
        dom.add_resource_dependency(ramo) if hasattr(dom, "add_resource_dependency") else dom.add_dependency(ramo)

        # o GitHub Actions envia o .zip do site para o Amplify. Política com nome próprio: o papel é importado
        # também na SonarTarefas, e a política automática do CDK teria o mesmo nome lá (conflito no IAM).
        papel = iam.Role.from_role_name(self, "PapelGitHub", PAPEL_DEPLOY)
        iam.Policy(self, "PermissoesDeploySite", policy_name="sonar-automais-deploy-site", roles=[papel],
                   statements=[
                       iam.PolicyStatement(
                           actions=["amplify:CreateDeployment", "amplify:StartDeployment", "amplify:GetJob",
                                    "amplify:GetApp", "amplify:GetBranch", "amplify:GetDomainAssociation"],
                           resources=[self.app.attr_arn, f"{self.app.attr_arn}/*"]),
                       iam.PolicyStatement(
                           actions=["cloudformation:DescribeStacks"],
                           resources=[f"arn:aws:cloudformation:{self.region}:{self.account}:stack/SonarSite/*",
                                      f"arn:aws:cloudformation:{self.region}:{self.account}:stack/SonarApi/*"])])

        CfnOutput(self, "SiteUrl", value=f"https://{dominio}")
        CfnOutput(self, "ApiDominioUrl", value=f"https://{host_api}")
        CfnOutput(self, "AmplifyAppId", value=self.app.attr_app_id)
        CfnOutput(self, "AmplifyUrl", value=f"https://{RAMO}.{self.app.attr_default_domain}")
