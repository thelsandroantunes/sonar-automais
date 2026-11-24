"""PostgreSQL 16 no RDS (db.t4g.micro, uma zona, sub-rede isolada).

- Só a Lambda da API e as tarefas Fargate chegam na porta 5432.
- Autenticação IAM ligada: a API entra com o usuário `sonar_api` (sem senha; token de 15 min).
- O usuário mestre fica no Secrets Manager e só as tarefas Fargate (migração/coleta) o usam.
- TLS obrigatório, disco criptografado, proteção contra exclusão.
- Plano gratuito da conta "AWS (new)": backup automático de no máximo 1 dia e 20 GB sem crescimento automático
  (o RDS recusa mais que isso). No plano pago (produção): backup 7 dias e max_allocated_storage 50.
"""
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from constructs import Construct

from .rede import Rede

USUARIO_MESTRE = "sonar_admin"
USUARIO_API = "sonar_api"
NOME_BANCO = "sonar"


class Banco(Stack):
    def __init__(self, escopo: Construct, id_: str, *, rede: Rede, **kw) -> None:
        super().__init__(escopo, id_, **kw)
        parametros = rds.ParameterGroup(
            self, "Parametros", engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16),
            parameters={"rds.force_ssl": "1", "log_min_duration_statement": "1000",
                        "timezone": "America/Sao_Paulo"})
        self.instancia = rds.DatabaseInstance(
            self, "Postgres", instance_identifier="sonar-automais",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO),
            vpc=rede.vpc, vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            multi_az=False, publicly_accessible=False, database_name=NOME_BANCO,
            credentials=rds.Credentials.from_generated_secret(USUARIO_MESTRE),
            allocated_storage=20, storage_type=rds.StorageType.GP3,
            storage_encrypted=True, iam_authentication=True, parameter_group=parametros,
            backup_retention=Duration.days(1), preferred_backup_window="07:00-07:30",  # UTC = 03h–03h30 em Manaus
            deletion_protection=True, removal_policy=RemovalPolicy.SNAPSHOT,
            auto_minor_version_upgrade=True, enable_performance_insights=False,
            cloudwatch_logs_exports=["postgresql"],
            cloudwatch_logs_retention=logs.RetentionDays.ONE_MONTH)  # sem isso o log do RDS nunca expira (2.6)
        for sg, quem in ((rede.sg_api, "API"), (rede.sg_tarefas, "tarefas")):
            self.instancia.connections.allow_default_port_from(sg, f"PostgreSQL a partir de {quem}")
        CfnOutput(self, "BancoEndereco", value=self.instancia.db_instance_endpoint_address)
        CfnOutput(self, "BancoSegredo", value=self.instancia.secret.secret_name)
        CfnOutput(self, "BancoRecursoId", value=self.instancia.instance_resource_id,
                  description="usado na política rds-db:connect da API")
