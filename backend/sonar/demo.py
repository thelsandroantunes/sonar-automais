"""Dados fictícios de demonstração (dados-referencia/ficticios/*.json).

Usados quando PARCEIRO=ficticio / OFFLINE=1, nos testes e no modo demonstração. Placa desconhecida cai num dos veículos
de exemplo (escolha fixa pela soma das letras), para qualquer placa válida mostrar uma tela completa.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache

from . import placa as P
from .config import config

PASTA = "ficticios"


@lru_cache(maxsize=None)
def _ler(nome: str) -> dict:
    return json.loads((config.dados_referencia / PASTA / nome).read_text(encoding="utf-8"))


def veiculos() -> list[dict]:
    return _ler("veiculos.json")["veiculos"]


def veiculo(placa: str) -> dict:
    p = P.normalizar(placa)
    vs = veiculos()
    for v in vs:
        if v["placa"] in P.equivalentes(p):
            return v
    base = vs[sum(map(ord, p)) % 4]          # só os 4 cenários principais (limpo, atenção, crítico, moto)
    return {**base, "placa": p, "exemplo_de": base["placa"]}


def fipe_atual(v: dict) -> float:
    return float(list(v["fipe"].values())[-1])


def multas_publicadas(placa: str) -> list[dict]:
    alvo = P.equivalentes(placa)
    return [m for m in _ler("multas_diario_manaus.json")["registros"] if m["placa"] in alvo]


def leiloes() -> list[dict]:
    return _ler("leiloes_publicos.json")["lotes"]


def leiloes_da_placa(placa: str) -> list[dict]:
    alvo = P.equivalentes(placa)
    return [l for l in leiloes() if l["placa"] in alvo]


def taxas_detran_am() -> dict:
    return _ler("taxas_detran_am.json")


def estoque_revenda() -> dict:
    return _ler("estoque_revenda.json")


def parceiros_comissao() -> list[dict]:
    return _ler("parceiros_comissao.json")["parceiros"]


def modelos() -> list[dict]:
    """FIPE por modelo (sem placa): um por veículo de exemplo."""
    return [{"codigo_fipe": v["codigo_fipe"], "modelo": v["modelo"], "ano": v["ano"].split("/")[1], "tipo": v["tipo"],
             "valor": fipe_atual(v), "historico": v["fipe"]} for v in veiculos()]


def data_iso(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None
