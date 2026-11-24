"""Configuração lida de variáveis de ambiente (arquivo .env na raiz). Base copiada do LIC (licitamais/config.py)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # testes sem python-dotenv
    def load_dotenv(*_a, **_k):
        return False

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")


def _lista(nome: str, padrao: str = "") -> list[str]:
    return [x.strip().upper() for x in os.getenv(nome, padrao).split(",") if x.strip()]


@dataclass(frozen=True)
class Config:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://sonar:sonar@localhost:5432/sonar")
    db_auth: str = os.getenv("DB_AUTH", "senha")          # senha | iam (Lambda na AWS)
    auth_modo: str = os.getenv("AUTH_MODO", "dev")         # dev | cognito
    dev_jwt_segredo: str = os.getenv("DEV_JWT_SEGREDO", "troque-este-segredo-em-producao")
    cognito_issuer: str = os.getenv("COGNITO_ISSUER", "")
    cors_origens: list[str] = field(
        default_factory=lambda: [o.strip() for o in os.getenv("CORS_ORIGENS", "http://localhost:5173").split(",")])
    sal_hash: str = os.getenv("SAL_HASH", "sonar-sal-dev")
    offline: bool = os.getenv("OFFLINE", "0") == "1"
    ufs_regras: list[str] = field(default_factory=lambda: _lista("UFS_REGRAS", "AM"))
    parceiro: str = os.getenv("PARCEIRO", "ficticio")
    parceiro_chave: str = os.getenv("PARCEIRO_CHAVE", "")
    pagamentos: bool = os.getenv("PAGAMENTOS", "0") == "1"
    fipe_url: str = os.getenv("FIPE_URL", "https://parallelum.com.br/fipe/api/v1")
    pncp_url: str = os.getenv("PNCP_URL", "https://pncp.gov.br/api")
    dados_referencia: Path = Path(os.getenv("DADOS_REFERENCIA") or RAIZ / "dados-referencia")
    migracoes: Path = RAIZ / "backend" / "migracoes"


config = Config()
