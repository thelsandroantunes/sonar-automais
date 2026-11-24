"""Limite diário (FIPE grátis por plano) e hash curto. Copiado do LIC (licitamais/eventos.py), sem o log completo."""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .config import config
from .db import um
from .planos import limite_fipe

MANAUS = ZoneInfo("America/Manaus")   # o limite vira à meia-noite de Manaus (onda 1)


def hoje() -> date:
    return datetime.now(MANAUS).date()


def hash_curto(valor: str | None) -> str | None:
    if not valor:
        return None
    return hashlib.sha256(f"{config.sal_hash}:{valor}".encode()).hexdigest()[:32]


class LimiteExcedido(Exception):
    def __init__(self, limite: int, usadas: int):
        super().__init__(f"Limite diário de {limite} placas atingido")
        self.limite, self.usadas = limite, usadas


def ja_consultou_hoje(conn, chave: str, placa_hash: str) -> bool:
    """Repetir a mesma placa no dia não conta no limite (vem do cache)."""
    return bool(um(conn, "SELECT 1 FROM consulta_placa WHERE chave = %s AND placa_hash = %s AND dia = %s",
                   (chave, placa_hash, hoje())))


def consumir_fipe(conn, chave: str, plano: str, placa_hash: str) -> dict:
    """Conta uma placa nova no dia. Levanta LimiteExcedido se passar do limite do plano."""
    if ja_consultou_hoje(conn, chave, placa_hash):
        r = um(conn, "SELECT buscas FROM uso_diario WHERE chave = %s AND dia = %s", (chave, hoje()))
        return {"usadas": r["buscas"] if r else 0, "limite": limite_fipe(plano), "repetida": True}
    limite = limite_fipe(plano)
    r = um(conn, """INSERT INTO uso_diario (chave, dia, buscas) VALUES (%s, %s, 1)
                    ON CONFLICT (chave, dia) DO UPDATE SET buscas = uso_diario.buscas + 1
                    RETURNING buscas""", (chave, hoje()))
    if limite is not None and r["buscas"] > limite:
        conn.execute("UPDATE uso_diario SET buscas = buscas - 1 WHERE chave = %s AND dia = %s", (chave, hoje()))
        raise LimiteExcedido(limite, r["buscas"] - 1)
    conn.execute("""INSERT INTO consulta_placa (chave, placa_hash, dia) VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING""", (chave, placa_hash, hoje()))
    return {"usadas": r["buscas"], "limite": limite, "repetida": False}


def vezes_consultada(conn, placa_hash: str, dias: int = 30) -> int:
    """Contador da placa (diferencial): quantas pessoas diferentes consultaram nos últimos N dias."""
    r = um(conn, """SELECT count(DISTINCT chave) AS n FROM consulta_placa
                    WHERE placa_hash = %s AND dia > %s::date - %s""", (placa_hash, hoje(), dias))
    return int(r["n"]) if r else 0
