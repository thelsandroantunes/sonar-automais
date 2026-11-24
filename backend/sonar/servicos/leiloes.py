"""Radar de leilões públicos (Detran-AM, PRF, PNCP). Mesma regra do LIC: Grátis/visitante veem com 24 h de atraso;
Pro e Empresa na hora, com alerta."""
from __future__ import annotations

from datetime import date, timedelta

from .. import demo, planos


def radar(plano: str | None = "visitante", uf: str | None = "AM", hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    atraso = planos.atraso_radar(plano)
    lotes = []
    for l in demo.leiloes():
        if uf and l["uf"] != uf.upper():
            continue
        abaixo = round((1 - l["lance_inicial"] / l["fipe"]) * 100) if l.get("fipe") else None
        lotes.append({**l, "abaixo_fipe_pct": abaixo, "futuro": date.fromisoformat(l["data"]) >= hoje})
    lotes.sort(key=lambda x: (not x["futuro"], x["data"]))
    return {"plano": plano, "atraso_horas": atraso, "visivel_desde": (hoje - timedelta(hours=atraso)).isoformat(),
            "alerta_na_hora": atraso == 0, "lotes": lotes}
