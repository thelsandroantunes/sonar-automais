"""Para quem vende: “quanto pedir” (FIPE ajustada pelo estado do veículo, débitos a quitar antes)."""
from __future__ import annotations

from ..consulta import laudo

AJUSTE_ESTADO = {"otimo": 0.03, "bom": 0.0, "regular": -0.08}
DESCONTO_VENDA_RAPIDA = 0.05


def quanto_pedir(placa: str, estado: str = "bom") -> dict:
    if estado not in AJUSTE_ESTADO:
        raise ValueError(f"estado deve ser um de {sorted(AJUSTE_ESTADO)}")
    l, cadastro, fipe = laudo(placa, "completa")
    anuncie = round(fipe["valor"] * (1 + AJUSTE_ESTADO[estado]), -2)
    return {"placa": l.placa, "modelo": cadastro["modelo"], "fipe": fipe["valor"], "estado": estado,
            "anuncie_por": anuncie, "vender_rapido": round(anuncie * (1 - DESCONTO_VENDA_RAPIDA), -2),
            "debitos_a_quitar": l.debitos_total(), "pontos_de_atencao": l.pontos_de_atencao,
            "dica": "Laudo limpo no anúncio (vendedor verificado) ajuda a sustentar o preço."}
