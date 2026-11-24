"""Tabela FIPE pela API pública Parallelum (grátis). Placa → modelo vem do parceiro (ex.: APIBrasil, R$ 0,06)."""
from __future__ import annotations

import re

import httpx

from ..config import config

TIPOS = {"carro": "carros", "moto": "motos", "caminhao": "caminhoes"}


def valor_reais(texto: str) -> float:
    """'R$ 98.200,00' → 98200.0"""
    return float(re.sub(r"[^0-9,]", "", texto).replace(",", "."))


class ClienteFipe:
    def __init__(self, cliente: httpx.Client | None = None):
        self.cli = cliente or httpx.Client(base_url=config.fipe_url, timeout=20)

    def valor(self, tipo: str, marca: str, modelo: str, ano: str) -> dict:
        r = self.cli.get(f"/{TIPOS[tipo]}/marcas/{marca}/modelos/{modelo}/anos/{ano}")
        r.raise_for_status()
        d = r.json()
        return {"codigo_fipe": d.get("CodigoFipe"), "valor": valor_reais(d["Valor"]),
                "referencia": d.get("MesReferencia"), "modelo": d.get("Modelo")}


class FipeFicticia:
    """FIPE da demonstração (mesmo formato do ClienteFipe)."""

    def da_placa(self, placa: str) -> dict:
        from .. import demo
        v = demo.veiculo(placa)
        return {"codigo_fipe": v["codigo_fipe"], "valor": demo.fipe_atual(v), "referencia": list(v["fipe"])[-1],
                "modelo": v["modelo"], "historico": v["fipe"]}
