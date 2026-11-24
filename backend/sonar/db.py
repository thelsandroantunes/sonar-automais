"""Acesso ao PostgreSQL com psycopg 3 (sem ORM: SQL explícito)."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
import time

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from .config import config

_pool: ConnectionPool | None = None

# Disjuntor: depois que o banco falha, as próximas chamadas falham na hora (503 imediato) por PAUSA segundos,
# em vez de cada uma esperar 5 s pelo pool. Passada a pausa, a próxima chamada tenta de novo.
PAUSA_BANCO_FORA = 15.0
_fora_ate = 0.0


class BancoForaDoAr(psycopg.OperationalError):
    pass


def banco_fora() -> bool:
    return time.monotonic() < _fora_ate


def marcar_banco_fora() -> None:
    global _fora_ate
    _fora_ate = time.monotonic() + PAUSA_BANCO_FORA


class ConexaoIAM(psycopg.Connection):
    """No RDS com autenticação IAM a 'senha' é um token de 15 min: gera um novo a cada conexão aberta."""

    @classmethod
    def connect(cls, conninfo: str = "", **kwargs):
        import boto3  # já vem na Lambda; não é dependência local
        from psycopg.conninfo import conninfo_to_dict
        p = {**conninfo_to_dict(conninfo), **kwargs}
        kwargs["password"] = boto3.client("rds").generate_db_auth_token(
            DBHostname=p["host"], Port=int(p.get("port") or 5432), DBUsername=p["user"])
        kwargs.setdefault("sslmode", "require")
        return super().connect(conninfo, **kwargs)


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        iam = config.db_auth == "iam"
        # timeout: quanto esperar por uma conexão livre; connect_timeout: banco fora do ar falha rápido (503 na API)
        # na Lambda: 1 conexão por instância e renovada antes do token de 15 min expirar
        _pool = ConnectionPool(config.database_url, min_size=1, max_size=2 if iam else 5, open=True, timeout=5,
                               max_lifetime=600 if iam else 3600,
                               connection_class=ConexaoIAM if iam else psycopg.Connection,
                               kwargs={"row_factory": dict_row, "autocommit": False, "connect_timeout": 5})
    return _pool


def fechar_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def conexao(usuario_id: str | None = None) -> Iterator[psycopg.Connection]:
    """Transação; grava o usuário em sonar.usuario_id para a auditoria."""
    if banco_fora():
        raise BancoForaDoAr("banco indisponível há pouco; nova tentativa em instantes")
    try:
        with pool().connection() as conn:
            if usuario_id:
                conn.execute("SELECT set_config('sonar.usuario_id', %s, true)", (str(usuario_id),))
            yield conn
    except (PoolTimeout, psycopg.OperationalError) as e:
        # tempo da consulta esgotado (statement_timeout da fila) não é banco fora do ar: não liga o disjuntor
        if not isinstance(e, (BancoForaDoAr, psycopg.errors.QueryCanceled)):
            marcar_banco_fora()
        raise


def um(conn: psycopg.Connection, sql: str, params: Any = None) -> dict | None:
    return conn.execute(sql, params).fetchone()


def todos(conn: psycopg.Connection, sql: str, params: Any = None) -> list[dict]:
    return conn.execute(sql, params).fetchall()
