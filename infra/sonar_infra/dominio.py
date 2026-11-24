"""Zona DNS do domínio no Route 53 (US$ 0,50/mês). O Registro.br aponta para os 4 servidores desta zona.

Domínio registrado em 20/11/2026 no Registro.br (1 ano). Os registros (site, API, e-mail/SES) entram nas próximas
pilhas; esta só cria a zona e mostra os servidores DNS para colar no Registro.br.
"""
from aws_cdk import CfnOutput, Fn, RemovalPolicy, Stack
from aws_cdk import aws_route53 as r53
from constructs import Construct


class Dominio(Stack):
    def __init__(self, escopo: Construct, id_: str, *, nome: str, **kw) -> None:
        super().__init__(escopo, id_, **kw)
        self.zona = r53.PublicHostedZone(self, "Zona", zone_name=nome,
                                         comment="Sonar Auto+ (registrado no Registro.br)")
        self.zona.apply_removal_policy(RemovalPolicy.RETAIN)  # apagar a zona derrubaria o domínio
        CfnOutput(self, "ServidoresDNS", value=Fn.join(" ", self.zona.hosted_zone_name_servers),
                  description="Cole estes 4 no Registro.br: Domínio > DNS > Alterar servidores DNS")
        CfnOutput(self, "ZonaId", value=self.zona.hosted_zone_id)
