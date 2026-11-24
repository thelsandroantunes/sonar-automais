"""Tarefas de bastidor no Fargate (sub-etapa 2.2): migrações do banco e coleta do PNCP 2x por dia.

- Imagem: `backend/Dockerfile`, montada pelo GitHub Actions (o Windows do usuário não tem Docker) e enviada para o
  ECR `sonar-automais/tarefas` com a tag `latest` (cada execução usa a imagem mais nova; sem redeploy).
- Rede: sub-rede PÚBLICA com IP público só enquanto a tarefa roda (sem NAT Gateway) → fala com PNCP/BrasilAPI;
  o banco aceita a porta 5432 a partir do grupo `SgTarefas`.
- Banco: usuário mestre do Secrets Manager injetado pelo ECS (DB_HOST/DB_USUARIO/DB_SENHA…); TLS obrigatório.
- Agenda (EventBridge, cron em UTC; horário de Manaus = UTC-4), cada execução roda as migrações pendentes antes:
  - Brasil inteiro COMPLETO às 03:00 (07:00 UTC): `coleta.coletar --brasil` (27 UFs, menos as coletadas por
    completo há menos de 4 h) + `coleta.limpar` (itens de encerrados há 7 dias e editais há 90 dias que ninguém
    acompanha). Editais iguais ao que já temos são descartados (não relê itens). A 1ª vez lê os itens de todos os
    editais abertos do país (pode passar de 1 h); depois só os novos/alterados.
  - AM + UFs das empresas Pro/Empresa às 13:41 (17:41 UTC): quem paga vê os editais publicados de manhã.
  - Histórico de resultados (concorrência, 2.29) todo dia à 00:00 (04:00 UTC): `coleta.historico` — AM primeiro,
    depois os Estados de quem paga; relê os últimos 60 dias + recua 20 dias por noite até 12 meses; até 50 min.
  - Carga do histórico do Brasil (23/11/2026) de madrugada em rodadas de 50 min ("rodar e parar"): 01:00, 02:00, 05:00
    e 06:00 (05, 06, 09 e 10 UTC; 03:00–04:59 ficam livres para a coleta nacional — 24/11: a rodada das 04:00 batia
    com a nacional e o PNCP recusava as listas): `coleta.historico --brasil` — AM,
    resto do Norte, Nordeste, Centro-Oeste, Sudeste, Sul; cada rodada continua de onde a outra parou.
  - Dados públicos de apoio à decisão, etapa 1 (26/11/2026) às 09:23 (13:23 UTC), 40 min: `coleta.dados_publicos uasg
    fnde pagamentos` — UASG (1x/mês), repasses do FNDE (arquivo mensal) e "paga em dia" dos órgãos federais (arquivo
    diário do Portal da Transparência). Não usa o PNCP: não disputa com a coleta nem com o histórico; termina bem antes
    da coleta das 13:41.
  - Sob demanda (borda): UF sem coleta recente → só os publicados nos últimos N dias pelo plano, com fila.
"""
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as alvos
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

from .banco import Banco
from .rede import Rede

NOME_REPO = "sonar-automais/tarefas"
PAPEL_DEPLOY = "sonar-automais-deploy"


class Tarefas(Stack):
    def __init__(self, escopo: Construct, id_: str, *, rede: Rede, banco: Banco, ufs: str = "AM", **kw) -> None:
        super().__init__(escopo, id_, **kw)

        self.repo = ecr.Repository(
            self, "Repo", repository_name=NOME_REPO, image_scan_on_push=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[ecr.LifecycleRule(description="guarda só as 10 imagens mais novas", max_image_count=10)])
        # o GitHub Actions (papel OIDC da 2.1) envia a imagem e dispara a migração depois do push
        papel_github = iam.Role.from_role_name(self, "PapelGitHub", PAPEL_DEPLOY)
        self.repo.grant_pull_push(papel_github)

        self.cluster = ecs.Cluster(self, "Cluster", cluster_name="sonar-automais", vpc=rede.vpc,
                                   enable_fargate_capacity_providers=True)
        self.logs = logs_tarefas = logs.LogGroup(self, "Logs", log_group_name="/sonar-automais/tarefas",
                                     retention=logs.RetentionDays.ONE_MONTH, removal_policy=RemovalPolicy.DESTROY)

        self.tarefa = ecs.FargateTaskDefinition(
            self, "Tarefa", family="sonar-automais-tarefas", cpu=256, memory_limit_mib=1024,
            runtime_platform=ecs.RuntimePlatform(cpu_architecture=ecs.CpuArchitecture.X86_64,
                                                 operating_system_family=ecs.OperatingSystemFamily.LINUX))
        segredo = banco.instancia.secret
        self.tarefa.add_container(
            "coleta", container_name="coleta",
            image=ecs.ContainerImage.from_ecr_repository(self.repo, "latest"),
            command=["sh", "-c", "python -m coleta.migrar && python -m coleta.coletar"],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="tarefa", log_group=logs_tarefas),
            environment={"UFS_COLETA": ufs, "OFFLINE": "0", "AUTH_MODO": "cognito", "PYTHONUNBUFFERED": "1"},
            secrets={
                "DB_HOST": ecs.Secret.from_secrets_manager(segredo, "host"),
                "DB_PORT": ecs.Secret.from_secrets_manager(segredo, "port"),
                "DB_NOME": ecs.Secret.from_secrets_manager(segredo, "dbname"),
                "DB_USUARIO": ecs.Secret.from_secrets_manager(segredo, "username"),
                "DB_SENHA": ecs.Secret.from_secrets_manager(segredo, "password"),
            })

        # console do banco (scripts/banco_console.sh): ECS Exec precisa destes canais do SSM na tarefa
        self.tarefa.add_to_task_role_policy(iam.PolicyStatement(
            actions=["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel",
                     "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"], resources=["*"]))

        rede_tarefa = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        events.Rule(
            self, "Agenda", rule_name="sonar-automais-coleta",
            description="Coleta do PNCP: AM + UFs de quem paga, 13:41 (Manaus)",
            schedule=events.Schedule.cron(minute="41", hour="17"),
            targets=[alvos.EcsTask(
                cluster=self.cluster, task_definition=self.tarefa, subnet_selection=rede_tarefa,
                assign_public_ip=True, security_groups=[rede.sg_tarefas], task_count=1,
                platform_version=ecs.FargatePlatformVersion.LATEST,
                retry_attempts=2, max_event_age=Duration.hours(2))])

        # 2.29 (decisão do usuário 22/11): histórico de resultados (concorrência) todo dia à 00:00 de Manaus (04:00 UTC),
        # sozinho, para não atrapalhar: AM primeiro, depois os Estados de quem paga; 50 min (23/11: antes da carga)
        events.Rule(
            self, "AgendaHistorico", rule_name="sonar-automais-historico",
            description="Histórico de resultados do PNCP (concorrência): AM + Estados de quem paga, 00:00 (Manaus)",
            schedule=events.Schedule.cron(minute="0", hour="4"),
            targets=[alvos.EcsTask(
                cluster=self.cluster, task_definition=self.tarefa, subnet_selection=rede_tarefa,
                assign_public_ip=True, security_groups=[rede.sg_tarefas], task_count=1,
                platform_version=ecs.FargatePlatformVersion.LATEST,
                container_overrides=[alvos.ContainerOverride(
                    container_name="coleta",
                    command=["sh", "-c", "python -m coleta.migrar && python -m coleta.historico --minutos 50"])],
                retry_attempts=2, max_event_age=Duration.hours(2))])

        # 23/11/2026 (pedido do usuário): carga do histórico de 12 meses do Brasil todo, de madrugada, em rodadas de
        # 50 min — 01:00, 02:00, 05:00 e 06:00 de Manaus (24/11: saiu a das 04:00, que disputava o PNCP com a coleta
        # nacional das 03:00 e perdia as listas de quase todas as UFs). AM, Norte, Nordeste, Centro-Oeste, Sudeste, Sul; o que faltar
        # continua na madrugada seguinte. Trava no banco: rodadas nunca se sobrepõem.
        events.Rule(
            self, "AgendaCargaHistorico", rule_name="sonar-automais-historico-carga",
            description="Carga do histórico de concorrência do Brasil por região, rodadas de 50 min de madrugada (Manaus)",
            schedule=events.Schedule.cron(minute="0", hour="5,6,9,10"),
            targets=[alvos.EcsTask(
                cluster=self.cluster, task_definition=self.tarefa, subnet_selection=rede_tarefa,
                assign_public_ip=True, security_groups=[rede.sg_tarefas], task_count=1,
                platform_version=ecs.FargatePlatformVersion.LATEST,
                container_overrides=[alvos.ContainerOverride(
                    container_name="coleta",
                    command=["sh", "-c", "python -m coleta.migrar && python -m coleta.historico --brasil --minutos 50"])],
                retry_attempts=1, max_event_age=Duration.minutes(30))])

        # 26/11/2026 (etapa 1 das fontes que faltavam): Portal da Transparência e Compras.gov.br numa janela livre da
        # manhã — 09:23 de Manaus (13:23 UTC), 40 min. As madrugadas ficam como estão (PNCP: histórico, carga e coleta).
        events.Rule(
            self, "AgendaDadosPublicos", rule_name="sonar-automais-dados-publicos",
            description="Dados públicos (UASG, FNDE, prazo de pagamento federal), 09:23 (Manaus)",
            schedule=events.Schedule.cron(minute="23", hour="13"),
            targets=[alvos.EcsTask(
                cluster=self.cluster, task_definition=self.tarefa, subnet_selection=rede_tarefa,
                assign_public_ip=True, security_groups=[rede.sg_tarefas], task_count=1,
                platform_version=ecs.FargatePlatformVersion.LATEST,
                container_overrides=[alvos.ContainerOverride(
                    container_name="coleta",
                    command=["sh", "-c", "python -m coleta.migrar && python -m coleta.dados_publicos uasg fnde pagamentos"
                                         " --minutos 40"])],
                retry_attempts=1, max_event_age=Duration.hours(1))])

        events.Rule(
            self, "AgendaBrasil", rule_name="sonar-automais-coleta-brasil",
            description="Coleta nacional completa do PNCP (27 UFs) + limpeza, 03:00 (Manaus)",
            schedule=events.Schedule.cron(minute="0", hour="7"),
            targets=[alvos.EcsTask(
                cluster=self.cluster, task_definition=self.tarefa, subnet_selection=rede_tarefa,
                assign_public_ip=True, security_groups=[rede.sg_tarefas], task_count=1,
                platform_version=ecs.FargatePlatformVersion.LATEST,
                container_overrides=[alvos.ContainerOverride(
                    container_name="coleta",
                    command=["sh", "-c", "python -m coleta.migrar && python -m coleta.coletar --brasil"
                                         " && python -m coleta.limpar"])],
                retry_attempts=2, max_event_age=Duration.hours(2))])

        # o GitHub Actions pode disparar uma execução avulsa (migração logo depois de enviar uma imagem nova)
        papel_github.add_to_principal_policy(iam.PolicyStatement(
            actions=["ecs:RunTask"],
            resources=[f"arn:aws:ecs:{self.region}:{self.account}:task-definition/sonar-automais-tarefas:*"]))
        papel_github.add_to_principal_policy(iam.PolicyStatement(
            actions=["cloudformation:DescribeStacks"],
            resources=[f"arn:aws:cloudformation:{self.region}:{self.account}:stack/SonarTarefas/*"]))
        papel_github.add_to_principal_policy(iam.PolicyStatement(
            actions=["iam:PassRole"], resources=[self.tarefa.task_role.role_arn,
                                                 self.tarefa.obtain_execution_role().role_arn]))

        publicas = ",".join(s.subnet_id for s in rede.vpc.public_subnets)
        CfnOutput(self, "RepoUri", value=self.repo.repository_uri)
        CfnOutput(self, "RodarAgora", description="Roda migrações + coleta na hora (CloudShell)", value=(
            f"aws ecs run-task --cluster sonar-automais --task-definition sonar-automais-tarefas "
            f"--launch-type FARGATE --network-configuration \"awsvpcConfiguration={{subnets=[{publicas}],"
            f"securityGroups=[{rede.sg_tarefas.security_group_id}],assignPublicIp=ENABLED}}\""))
