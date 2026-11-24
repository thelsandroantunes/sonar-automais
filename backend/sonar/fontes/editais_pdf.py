"""Leitura de editais publicados em PDF (texto já extraído): multas da IMMU no Diário Oficial de Manaus e resenhas de
notificação de leilão do Detran-AM. O PDF vira texto fora daqui (pdftotext/pypdf); aqui só a interpretação.

Formato visto nos editais da IMMU: "JWK-5658 MT01864090 554-1/2 28/10" (placa, auto, código da infração, dia/mês).
"""
from __future__ import annotations

import re

from .. import placa as P

_LINHA_IMMU = re.compile(
    r"\b([A-Z]{3}[\s-]?[0-9][A-Z0-9][0-9]{2})\s+([A-Z]{2}\d{6,10})\s+(\d{3}-\d(?:/\d)?)\s+(\d{2}/\d{2}(?:/\d{2,4})?)")


def notificacoes_immu(texto: str, ano: int | None = None) -> list[dict]:
    out = []
    for placa, auto, codigo, data in _LINHA_IMMU.findall((texto or "").upper()):
        p = P.normalizar(placa)
        if P.valida(p):
            out.append({"placa": p, "auto": auto, "codigo_infracao": codigo, "data": data, "ano": ano,
                        "fonte": "immu_dom"})
    return out


def placas_resenha_leilao(texto: str) -> list[str]:
    """Resenha de notificação de leilão do Detran-AM: lista de veículos em pátio que irão a leilão."""
    return P.no_texto(texto)
