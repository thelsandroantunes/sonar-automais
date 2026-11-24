"""Leilões públicos de veículos no PNCP (modalidades 1 = leilão eletrônico, 13 = leilão presencial).

Usa o mesmo cliente do LIC (sonar/pncp.py, copiado de licitamais/pncp.py). Validado em 24/11/2026: 137 leilões
publicados no Brasil de 1 a 24/11; 33 dos 300 primeiros com veículos e alguns com a placa no texto do objeto.
As placas também aparecem na descrição dos itens (/orgaos/{cnpj}/compras/{ano}/{seq}/itens).
"""
from __future__ import annotations

import re
from datetime import date

from .. import placa as P

MODALIDADES_LEILAO = (1, 13)
_VEICULO = re.compile(r"ve[ií]culo|autom[oó]vel|motocicleta|caminh[aã]o|camionete|caminhonete|[ôo]nibus|sucata",
                      re.I)


def e_de_veiculo(texto: str) -> bool:
    return bool(_VEICULO.search(texto or ""))


def registros(contratacao: dict, itens: list[dict] | None = None) -> list[dict]:
    """Uma linha por placa citada no leilão (objeto + itens)."""
    textos = [contratacao.get("objetoCompra") or ""] + [i.get("descricao") or "" for i in (itens or [])]
    if not any(e_de_veiculo(t) for t in textos):
        return []
    org = contratacao.get("orgaoEntidade") or {}
    uni = contratacao.get("unidadeOrgao") or {}
    placas: list[str] = []
    for t in textos:
        for p in P.no_texto(t):
            if p not in placas:
                placas.append(p)
    return [{"placa": p, "fonte": "pncp", "orgao": org.get("razaoSocial"), "uf": uni.get("ufSigla"),
             "modalidade": contratacao.get("modalidadeNome"),
             "data": (contratacao.get("dataPublicacaoPncp") or "")[:10],
             "url": contratacao.get("linkSistemaOrigem")} for p in placas]


def janela(dias: int = 30) -> tuple[date, date]:
    from datetime import timedelta
    fim = date.today()
    return fim - timedelta(days=dias), fim
