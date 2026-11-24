"""Monitoramento de placa (adaptado de licitamais/alertas.py): quando uma coleta traz algo novo para uma placa
monitorada — multa publicada, leilão, mudança no parceiro (gravame baixado, nova restrição) — vira alerta.
Só planos com monitoramento (Completa 30 dias, Pro 50 placas, Empresa 300)."""
from __future__ import annotations

from .db import todos


def gerar(conn, placa_hashes: list[str], tipo: str, detalhe: str) -> int:
    if not placa_hashes:
        return 0
    linhas = todos(conn, """
        INSERT INTO alerta (usuario_id, monitoramento_id, tipo, detalhe)
        SELECT m.usuario_id, m.id, %s, %s
        FROM monitoramento m
        WHERE m.placa_hash = ANY(%s) AND m.ativo AND (m.ate IS NULL OR m.ate > now())
        ON CONFLICT (monitoramento_id, tipo, detalhe) DO NOTHING
        RETURNING id""", (tipo, detalhe, placa_hashes))
    return len(linhas)
