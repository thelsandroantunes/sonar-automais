"""Rede sem NAT Gateway (decisão do projeto: NAT custa ~US$ 35+/mês).

- Sub-redes PÚBLICAS: tarefas Fargate (coleta/migração) com IP público para falar com PNCP/BrasilAPI.
- Sub-redes ISOLADAS (sem internet): RDS e a Lambda da API.
"""
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class Rede(Stack):
    def __init__(self, escopo: Construct, id_: str, **kw) -> None:
        super().__init__(escopo, id_, **kw)
        self.vpc = ec2.Vpc(
            self, "Vpc", vpc_name="sonar-automais", ip_addresses=ec2.IpAddresses.cidr("10.40.0.0/16"),
            availability_zones=[f"{self.region}a", f"{self.region}b"], nat_gateways=0,
            restrict_default_security_group=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="publica", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(name="isolada", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24),
            ])
        # grupos de segurança de quem pode falar com o banco
        self.sg_api = ec2.SecurityGroup(self, "SgApi", vpc=self.vpc, description="Lambda da API",
                                        allow_all_outbound=True)
        self.sg_tarefas = ec2.SecurityGroup(self, "SgTarefas", vpc=self.vpc,
                                            description="Fargate: coleta e migracoes", allow_all_outbound=True)
