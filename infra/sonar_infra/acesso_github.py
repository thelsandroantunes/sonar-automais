"""Acesso do GitHub Actions à AWS por OIDC (sem chave guardada em lugar nenhum).

Implantado UMA vez pelo AWS CloudShell (navegador). Depois disso, todo deploy roda no GitHub Actions,
que assume o papel `sonar-automais-deploy` só a partir deste repositório e do ramo main.
"""
from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_iam as iam
from constructs import Construct


class AcessoGitHub(Stack):
    def __init__(self, escopo: Construct, id_: str, *, repo: str, repo_ids: str | None = None, **kw) -> None:
        super().__init__(escopo, id_, **kw)
        provedor = iam.OpenIdConnectProvider(
            self, "GitHubOIDC", url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"])
        # O GitHub passou a mandar o "sub" com IDs fixos (dono@id/repo@id). Aceitamos os dois formatos;
        # os IDs não mudam se o repositório for renomeado e impedem que outro repositório com o mesmo nome entre.
        nomes = [repo] + ([repo_ids] if repo_ids else [])
        papel = iam.Role(
            self, "PapelDeploy", role_name="sonar-automais-deploy", max_session_duration=Duration.hours(1),
            description="GitHub Actions (main) faz cdk deploy do Sonar Auto+",
            assumed_by=iam.WebIdentityPrincipal(provedor.open_id_connect_provider_arn, conditions={
                "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
                "StringLike": {"token.actions.githubusercontent.com:sub": [
                    f"repo:{r}:{fim}" for r in nomes for fim in ("ref:refs/heads/main", "environment:producao")]},
            }))
        # o deploy só assume os papéis que o `cdk bootstrap` criou (cdk-hnb659fds-*), e não ganha admin direto
        papel.add_to_policy(iam.PolicyStatement(
            actions=["sts:AssumeRole"], resources=[f"arn:aws:iam::{self.account}:role/cdk-hnb659fds-*"]))
        CfnOutput(self, "PapelDeployArn", value=papel.role_arn,
                  description="Coloque no GitHub: Settings > Secrets and variables > Actions > Variables > AWS_PAPEL_DEPLOY")
