"""API na AWS (sub-etapa 2.3): API Gateway HTTP → Lambda "borda" → Lambda da API (na VPC) → RDS.

- Lambda da API (`sonar-automais-api`): FastAPI + Mangum, nas sub-redes ISOLADAS (sem internet, sem NAT),
  entra no RDS como `sonar_api` com token IAM (sem senha). Só a borda pode invocá-la.
- Lambda "borda" (`sonar-automais-borda`): fora da VPC. Valida o login do Cognito (claims no evento),
  consulta a BrasilAPI nas rotas com CNPJ e invoca a Lambda da API. Detalhes em backend/borda/handler.py.
- Cognito: cadastro e login por e-mail + senha (e-mail de verificação do próprio Cognito, até 50/dia; SES na 2.7).
- API Gateway HTTP com limite de 20 req/s (pico 40) para conter custo e abuso.
- Código das duas Lambdas: pasta build/lambda, montada por scripts/pacote_lambda.sh no GitHub Actions (api.yml).
  Sem a pasta (testes, CloudShell) entra um código provisório — por isso a SonarApi só é implantada pelo workflow.
"""
from pathlib import Path

from aws_cdk import Annotations, CfnOutput, Duration, RemovalPolicy, SecretValue, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_integrations as integ
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as sm
from constructs import Construct

from .banco import NOME_BANCO, USUARIO_API, Banco
from .rede import Rede

PACOTE = Path(__file__).resolve().parents[2] / "build" / "lambda"
PROVISORIO = ("import json\n"
              "def handler(e, c):\n"
              "    return {'statusCode': 503, 'body': json.dumps({'detail': 'API ainda nao implantada pelo "
              "workflow api.yml', 'codigo': 'servidor_indisponivel'})}\n")


class Api(Stack):
    def __init__(self, escopo: Construct, id_: str, *, rede: Rede, banco: Banco, dominio: str | None = None,
                 tarefas=None, ses_cognito: bool = False, google: bool = False, asaas: str = "",
                 **kw) -> None:
        super().__init__(escopo, id_, **kw)
        if PACOTE.exists():
            codigo = lambda_.Code.from_asset(str(PACOTE))
        else:
            codigo = lambda_.Code.from_inline(PROVISORIO)
            Annotations.of(self).add_warning("build/lambda não existe: Lambdas com código provisório "
                                             "(rode scripts/pacote_lambda.sh ou implante pelo workflow api.yml)")
        site = f"https://{dominio},https://www.{dominio}" if dominio else "http://localhost:5173"

        # ---------------------------------------------------------------- login (Cognito)
        # E-mails do login: pelo próprio Cognito (no-reply@verificationemail.com, ~50/dia) até o SES do domínio sair
        # do sandbox; depois, "ses_cognito": true no cdk.json → nao-responda@<domínio> (2.7, pilha SonarEmail).
        email = (cognito.UserPoolEmail.with_ses(
            from_email=f"nao-responda@{dominio}", from_name="Sonar Auto+", reply_to=f"contato@{dominio}",
            ses_region=self.region, ses_verified_domain=dominio) if ses_cognito and dominio
            else cognito.UserPoolEmail.with_cognito())
        self.usuarios = cognito.UserPool(
            self, "Usuarios", user_pool_name="sonar-automais", self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True), sign_in_case_sensitive=False,
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(email=cognito.StandardAttribute(required=True,
                                                                                           mutable=True)),
            # 8+ caracteres com pelo menos 1 número (maiúsculas/minúsculas livres: exigir minúscula travou usuário real)
            password_policy=cognito.PasswordPolicy(min_length=8, require_lowercase=False, require_digits=True,
                                                   require_uppercase=False, require_symbols=False,
                                                   temp_password_validity=Duration.days(7)),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY, email=email,
            user_verification=cognito.UserVerificationConfig(
                email_subject="Sonar Auto+: seu código",
                email_body=("Olá! Seu código do Sonar Auto+ é {####}. Ele vale por 24 horas. "
                            "Se não foi você que pediu, ignore este e-mail."),
                email_style=cognito.VerificationEmailStyle.CODE),
            user_invitation=cognito.UserInvitationConfig(
                email_subject="Sonar Auto+: sua conta foi criada",
                email_body=("Olá! Criamos sua conta no Sonar Auto+ (https://" + (dominio or "sonarautomais.com.br")
                            + "). Entre com o e-mail {username} e a senha temporária {####}; no primeiro acesso "
                            "você define a sua senha. A senha temporária vale 7 dias.")),
            deletion_protection=True, removal_policy=RemovalPolicy.RETAIN)

        # 24/11/2026: cadastro curto de quem veio de "Assinar" (confirma sem o código; e-mail verificado depois)
        gatilho = lambda_.Function(
            self, "GatilhoCadastro", function_name="sonar-automais-pre-cadastro", runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler", timeout=Duration.seconds(5), memory_size=128,
            code=lambda_.Code.from_inline((Path(__file__).parent / "gatilho_cadastro.py").read_text(encoding="utf-8")),
            log_group=logs.LogGroup(self, "LogsPreCadastro", log_group_name="/sonar-automais/pre-cadastro",
                                    retention=logs.RetentionDays.ONE_MONTH, removal_policy=RemovalPolicy.DESTROY))
        # ARN com curinga (não o do próprio pool) para não criar dependência circular pool ↔ gatilho
        gatilho.add_to_role_policy(iam.PolicyStatement(
            actions=["cognito-idp:ListUsers"],
            resources=[self.format_arn(service="cognito-idp", resource="userpool", resource_name="*")]))
        self.usuarios.add_trigger(cognito.UserPoolOperation.PRE_SIGN_UP, gatilho)

        # Domínio do login da AWS (prefixo; domínio próprio exigiria certificado em us-east-1, bloqueado na conta):
        # usado só no "Entrar com Google" (OAuth com PKCE; a tela é a do Google).
        self.dominio_login = self.usuarios.add_domain(
            "DominioLogin", cognito_domain=cognito.CognitoDomainOptions(domain_prefix="sonar-automais"))
        provedores = [cognito.UserPoolClientIdentityProvider.COGNITO]
        google_idp = None
        if google:
            # client_id e client_secret do Google ficam no Secrets Manager (criados à mão no CloudShell; nunca no Git)
            segredo_google = "sonar-automais/google-oauth"
            google_idp = cognito.UserPoolIdentityProviderGoogle(
                self, "Google", user_pool=self.usuarios,
                client_id=SecretValue.secrets_manager(segredo_google, json_field="client_id").unsafe_unwrap(),
                client_secret_value=SecretValue.secrets_manager(segredo_google, json_field="client_secret"),
                scopes=["openid", "email", "profile"],
                attribute_mapping=cognito.AttributeMapping(
                    email=cognito.ProviderAttribute.GOOGLE_EMAIL,
                    fullname=cognito.ProviderAttribute.GOOGLE_NAME,
                    custom={"email_verified": cognito.ProviderAttribute.other("email_verified")}))
            # O Cognito (login clássico) não repassa prompt=select_account ao Google: sem isto, quem tem várias contas
            # Google no navegador entra direto na última usada. Pedindo a escolha no próprio endereço do Google:
            google_idp.node.default_child.add_property_override(
                "ProviderDetails.authorize_url", "https://accounts.google.com/o/oauth2/v2/auth?prompt=select_account")
            provedores.append(cognito.UserPoolClientIdentityProvider.GOOGLE)
        retornos = [f"https://{dominio}/entrar", f"https://www.{dominio}/entrar"] if dominio else []
        retornos.append("http://localhost:5173/entrar")
        self.cliente = self.usuarios.add_client(
            "Site", user_pool_client_name="site", generate_secret=False,
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
            supported_identity_providers=provedores,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
                callback_urls=retornos, logout_urls=[u.removesuffix("/entrar") + "/" for u in retornos]),
            prevent_user_existence_errors=True, id_token_validity=Duration.hours(1),
            access_token_validity=Duration.hours(1), refresh_token_validity=Duration.days(30))
        if google_idp:
            self.cliente.node.add_dependency(google_idp)
        # antes do Asaas, só quem está neste grupo pode trocar de plano (simulação) — ver api/auth.py
        cognito.CfnUserPoolGroup(self, "Testadores", user_pool_id=self.usuarios.user_pool_id,
                                 group_name="testadores", description="Podem trocar de plano sem pagar (testes)")
        issuer = f"https://cognito-idp.{self.region}.amazonaws.com/{self.usuarios.user_pool_id}"

        # sal dos hashes de IP/navegador (visitantes): gerado na AWS, nunca no Git
        sal = sm.Secret(self, "Sal", description="Sonar Auto+: sal dos hashes de visitante",
                        generate_secret_string=sm.SecretStringGenerator(password_length=40,
                                                                        exclude_punctuation=True))

        # ---------------------------------------------------------------- Lambda da API (VPC)
        self.logs_api = logs_api = logs.LogGroup(self, "LogsApi", log_group_name="/sonar-automais/api",
                                 retention=logs.RetentionDays.ONE_MONTH, removal_policy=RemovalPolicy.DESTROY)
        self.funcao_api = lambda_.Function(
            self, "FuncaoApi", function_name="sonar-automais-api", runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64, code=codigo,
            handler="api.main.handler" if PACOTE.exists() else "index.handler",
            memory_size=1024, timeout=Duration.seconds(25), log_group=logs_api,
            vpc=rede.vpc, vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[rede.sg_api],
            environment={
                "DB_HOST": banco.instancia.db_instance_endpoint_address, "DB_PORT": "5432",
                "DB_NOME": NOME_BANCO, "DB_USUARIO": USUARIO_API, "DB_AUTH": "iam", "DB_SSLMODE": "require",
                "AUTH_MODO": "cognito", "COGNITO_ISSUER": issuer, "CNPJ_VIA_BORDA": "1", "OFFLINE": "0",
                "COLETA_SOB_DEMANDA": "1" if tarefas else "0",
                "METRICAS_LOG": "1",  # uma linha JSON por requisição → métricas do CloudWatch (2.6)
                "CORS_ORIGENS": site, "DADOS_REFERENCIA": "/var/task/dados-referencia",
                "API_PREFIXO": "/api",  # aceita /api/... e /... (site chama api.<domínio>/...)
                "SAL_HASH": sal.secret_value.unsafe_unwrap(),  # referência dinâmica: o valor não fica no template
            })
        self.funcao_api.add_to_role_policy(iam.PolicyStatement(
            actions=["rds-db:connect"],
            resources=[f"arn:aws:rds-db:{self.region}:{self.account}:dbuser:"
                       f"{banco.instancia.instance_resource_id}/{USUARIO_API}"]))

        # ---------------------------------------------------------------- Lambda "borda" (fora da VPC)
        self.logs_borda = logs_borda = logs.LogGroup(self, "LogsBorda", log_group_name="/sonar-automais/borda",
                                   retention=logs.RetentionDays.ONE_MONTH, removal_policy=RemovalPolicy.DESTROY)
        self.borda = lambda_.Function(
            self, "FuncaoBorda", function_name="sonar-automais-borda", runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64, code=codigo,
            handler="borda.handler.handler" if PACOTE.exists() else "index.handler",
            memory_size=256, timeout=Duration.seconds(29), log_group=logs_borda,
            environment={"API_FUNCAO": self.funcao_api.function_name, "COGNITO_ISSUER": issuer,
                         "COGNITO_CLIENTE": self.cliente.user_pool_client_id, "OFFLINE": "0",
                         "CORS_ORIGENS": site,  # a borda também responde 401/502 com CORS
                         "DADOS_REFERENCIA": "/var/task/dados-referencia"})
        self.funcao_api.grant_invoke(self.borda)

        # 2.30: cópia dos PDFs dos editais (só assinantes Pro/Empresa) para quando o PNCP sai do ar.
        # Bucket privado (sem acesso público); a borda grava e entrega por link assinado (1 h). Vence em 180 dias.
        self.documentos = s3.Bucket(
            self, "Documentos", block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED, enforce_ssl=True, versioned=False,
            lifecycle_rules=[s3.LifecycleRule(id="vence-180-dias", expiration=Duration.days(180))],
            removal_policy=RemovalPolicy.RETAIN)
        self.documentos.grant_read_write(self.borda)
        self.borda.add_environment("DOCS_BUCKET", self.documentos.bucket_name)
        # a borda chama a si mesma (assíncrono) para baixar e guardar sem a tela esperar
        self.borda.add_to_role_policy(iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=[f"arn:aws:lambda:{self.region}:{self.account}:function:sonar-automais-borda"]))

        # painel de administração: a borda faz no Cognito o que o administrador pede (a API confere antes)
        self.borda.add_environment("USER_POOL_ID", self.usuarios.user_pool_id)
        self.borda.add_to_role_policy(iam.PolicyStatement(
            actions=["cognito-idp:AdminCreateUser", "cognito-idp:AdminSetUserPassword",
                     "cognito-idp:AdminConfirmSignUp", "cognito-idp:AdminDisableUser", "cognito-idp:AdminEnableUser",
                     "cognito-idp:AdminDeleteUser", "cognito-idp:AdminUserGlobalSignOut", "cognito-idp:AdminGetUser"],
            resources=[self.usuarios.user_pool_arn]))

        # coleta sob demanda: a busca de um CNPJ de UF não coletada hoje → a borda roda a tarefa do Fargate
        if tarefas is not None:
            for k, v in {"COLETA_CLUSTER": tarefas.cluster.cluster_name,
                         "COLETA_TAREFA": tarefas.tarefa.family,
                         "COLETA_SUBREDES": ",".join(s.subnet_id for s in rede.vpc.public_subnets),
                         "COLETA_SG": rede.sg_tarefas.security_group_id}.items():
                self.borda.add_environment(k, v)
            self.borda.add_to_role_policy(iam.PolicyStatement(
                actions=["ecs:RunTask"],
                resources=[f"arn:aws:ecs:{self.region}:{self.account}:task-definition/{tarefas.tarefa.family}:*"],
                conditions={"ArnEquals": {"ecs:cluster": tarefas.cluster.cluster_arn}}))
            self.borda.add_to_role_policy(iam.PolicyStatement(
                actions=["iam:PassRole"], resources=[tarefas.tarefa.task_role.role_arn,
                                                     tarefas.tarefa.obtain_execution_role().role_arn]))

        # ---------------------------------------------------------------- Etapa 4: assinaturas pelo Asaas
        # contexto "asaas" = "sandbox" (testes) | "producao" | "" (desligado). A chave da API e o token do webhook
        # ficam no segredo sonar-automais/asaas (criado à mão no CloudShell; nunca no Git). Só a borda lê o segredo
        # e fala com o Asaas; a API (VPC) só recebe o resultado.
        if asaas in ("sandbox", "producao"):
            segredo_asaas = sm.Secret.from_secret_name_v2(self, "SegredoAsaas", "sonar-automais/asaas")
            self.borda.add_environment("ASAAS_URL", "https://api-sandbox.asaas.com/v3" if asaas == "sandbox"
                                       else "https://api.asaas.com/v3")
            self.borda.add_environment("ASAAS_SEGREDO", "sonar-automais/asaas")
            segredo_asaas.grant_read(self.borda)
            self.funcao_api.add_environment("PAGAMENTOS", "1")
            CfnOutput(self, "AsaasWebhook", value=f"https://api.{dominio}/asaas/webhook" if dominio else "/asaas/webhook",
                      description="Asaas > Integrações > Webhooks: URL deste aviso (token = webhook_token do segredo)")
        CfnOutput(self, "PagamentosAtivos", value=asaas or "desligado")

        # ---------------------------------------------------------------- e-mail de boas-vindas (Cognito → SES)
        # Gatilho "pós-confirmação": cadastro confirmado ou 1º login com o Google → e-mail pelo SES do domínio.
        # Só com o SES fora do sandbox (mesma chave "ses_cognito"). O código nunca levanta erro (borda/boas_vindas.py).
        if ses_cognito and dominio:
            logs_bv = logs.LogGroup(self, "LogsBoasVindas", log_group_name="/sonar-automais/boas-vindas",
                                    retention=logs.RetentionDays.ONE_MONTH, removal_policy=RemovalPolicy.DESTROY)
            self.boas_vindas = lambda_.Function(
                self, "FuncaoBoasVindas", function_name="sonar-automais-boas-vindas",
                runtime=lambda_.Runtime.PYTHON_3_12, architecture=lambda_.Architecture.X86_64, code=codigo,
                handler="borda.boas_vindas.handler" if PACOTE.exists() else "index.handler",
                memory_size=128, timeout=Duration.seconds(4),  # o Cognito espera no máximo 5 s
                log_group=logs_bv,
                environment={"REMETENTE": f"Sonar Auto+ <nao-responda@{dominio}>",
                             "RESPONDER_PARA": f"contato@{dominio}", "SITE": f"https://{dominio}"})
            self.boas_vindas.add_to_role_policy(iam.PolicyStatement(
                actions=["ses:SendEmail"],
                resources=[f"arn:aws:ses:{self.region}:{self.account}:identity/{dominio}"]))
            self.usuarios.add_trigger(cognito.UserPoolOperation.POST_CONFIRMATION, self.boas_vindas)

        # ---------------------------------------------------------------- API Gateway HTTP
        self.http = apigw.HttpApi(
            self, "Http", api_name="sonar-automais",
            default_integration=integ.HttpLambdaIntegration("Borda", self.borda))
        estagio = self.http.default_stage.node.default_child
        estagio.add_property_override("DefaultRouteSettings",
                                      {"ThrottlingRateLimit": 20, "ThrottlingBurstLimit": 40})

        CfnOutput(self, "ApiUrl", value=self.http.api_endpoint, description="teste: <ApiUrl>/saude")
        CfnOutput(self, "UserPoolId", value=self.usuarios.user_pool_id)
        CfnOutput(self, "ClienteId", value=self.cliente.user_pool_client_id)
        CfnOutput(self, "CognitoIssuer", value=issuer)
        CfnOutput(self, "CognitoDominio", value=f"{self.dominio_login.domain_name}.auth.{self.region}.amazoncognito.com",
                  description="Google Cloud: URI de redirecionamento = https://<este>/oauth2/idpresponse")
        CfnOutput(self, "GoogleAtivo", value="1" if google else "0")
