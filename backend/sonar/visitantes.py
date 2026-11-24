"""Visitante persistente — copiado do LIC (licitamais/visitantes.py), adaptado: o limite de placas FIPE sem cadastro
não zera se a pessoa limpar o cache. Identificação: cookie rx_vid → impressão (hash de IP + navegador + idioma,
90 dias) → novo. Teto por IP no dia para quem troca de navegador ou abre janela anônima.
"""
from __future__ import annotations

import uuid

from .db import um
from .eventos import LimiteExcedido, consumir_fipe, hash_curto, hoje

COOKIE = "rx_vid"
DIAS_IMPRESSAO = 90
TETO_IP_DIA = 40   # várias pessoas podem dividir o IP (empresa, escola, revenda)


def impressao(ip: str | None, user_agent: str | None, idioma: str | None) -> str:
    return hash_curto(f"{ip or ''}|{(user_agent or '')[:300]}|{(idioma or '')[:60]}") or "anonimo"


def _uuid(v: str | None) -> str | None:
    try:
        return str(uuid.UUID(v)) if v else None
    except ValueError:
        return None


def identificar(conn, cookie: str | None, ip: str | None, user_agent: str | None, idioma: str | None
                ) -> tuple[dict, bool]:
    imp, ip_h = impressao(ip, user_agent, idioma), hash_curto(ip)
    v = um(conn, "SELECT * FROM visitante WHERE id = %s", (_uuid(cookie),)) if _uuid(cookie) else None
    regravar = v is None
    if v is None:
        v = um(conn, """SELECT * FROM visitante WHERE impressao = %s
                         AND ultimo_acesso > now() - make_interval(days => %s)
                        ORDER BY ultimo_acesso DESC LIMIT 1""", (imp, DIAS_IMPRESSAO))
    if v is None:
        return um(conn, "INSERT INTO visitante (impressao, ip_hash) VALUES (%s, %s) RETURNING *", (imp, ip_h)), True
    v = um(conn, "UPDATE visitante SET ultimo_acesso = now(), ip_hash = %s WHERE id = %s RETURNING *",
           (ip_h, v["id"]))
    return v, regravar


def consumir(conn, v: dict, placa_hash: str) -> dict:
    r = consumir_fipe(conn, f"v:{v['id']}", "visitante", placa_hash)
    if r["repetida"]:
        return r
    ip = um(conn, """INSERT INTO uso_diario (chave, dia, buscas) VALUES (%s, %s, 1)
                     ON CONFLICT (chave, dia) DO UPDATE SET buscas = uso_diario.buscas + 1
                     RETURNING buscas""", (f"ip:{v['ip_hash'] or 'anonimo'}", hoje()))
    if ip["buscas"] > TETO_IP_DIA:
        raise LimiteExcedido(TETO_IP_DIA, TETO_IP_DIA)
    return r
