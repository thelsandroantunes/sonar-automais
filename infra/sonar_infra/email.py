"""E-mail do domínio pelo Amazon SES (sub-etapa 2.7): identidade sonarautomais.com.br com DKIM, MAIL FROM e DMARC.

Tudo vai para a zona da Route 53 automaticamente (o SES confirma o domínio sozinho em minutos).

- Remetente dos e-mails do login (Cognito): nao-responda@sonarautomais.com.br — só depois que a AWS tirar a conta
  do "sandbox" do SES (pedido no console; no sandbox só dá para mandar para endereços verificados). Aí: "ses_cognito":
  true no cdk.json.
- MAIL FROM em mail.sonarautomais.com.br (SPF alinhado); DMARC começa em p=none (só observa) e depois sobe para
  quarantine quando os relatórios estiverem limpos.
- Receber e-mail (contato@): o SES só recebe em regiões que a conta não pode usar, então a raiz do domínio aponta
  o MX para o ImprovMX (plano grátis), que encaminha contato@ para o Gmail configurado no painel do ImprovMX.
  O destino do encaminhamento fica só lá, não no código. Responder "como contato@": Gmail → Enviar e-mail como,
  usando a credencial SMTP do SES (depois de sair do sandbox).
"""
from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_route53 as r53
from aws_cdk import aws_ses as ses
from constructs import Construct


class Email(Stack):
    def __init__(self, escopo: Construct, id_: str, *, dominio: str, zona_id: str, **kw) -> None:
        super().__init__(escopo, id_, **kw)
        zona = r53.HostedZone.from_hosted_zone_attributes(self, "Zona", hosted_zone_id=zona_id, zone_name=dominio)
        self.identidade = ses.EmailIdentity(
            self, "Dominio", identity=ses.Identity.public_hosted_zone(zona), mail_from_domain=f"mail.{dominio}")
        r53.TxtRecord(self, "Dmarc", zone=zona, record_name="_dmarc", ttl=Duration.hours(1),
                      values=["v=DMARC1; p=none; adkim=s; aspf=s"])
        # Recebimento (contato@ etc.) pelo ImprovMX. O SES envia com MAIL FROM em mail.<domínio>, que tem SPF
        # próprio; este SPF da raiz só cobre os servidores do ImprovMX.
        r53.MxRecord(self, "MxImprovMX", zone=zona, ttl=Duration.hours(1), values=[
            r53.MxRecordValue(host_name="mx1.improvmx.com", priority=10),
            r53.MxRecordValue(host_name="mx2.improvmx.com", priority=20)])
        r53.TxtRecord(self, "SpfRaiz", zone=zona, ttl=Duration.hours(1),
                      values=["v=spf1 include:spf.improvmx.com ~all"])
        CfnOutput(self, "Contato", value=f"contato@{dominio}",
                  description="Recebido pelo ImprovMX e encaminhado ao Gmail definido no painel do ImprovMX")
        CfnOutput(self, "Remetente", value=f"nao-responda@{dominio}")
