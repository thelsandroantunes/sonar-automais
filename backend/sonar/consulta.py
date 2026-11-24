"""Orquestra a consulta de uma placa: FIPE + base pública (multas no Diário Oficial, leilões públicos) + parceiro +
regras da UF → laudo. Hoje com dados fictícios; na Fase 1 cada fonte troca pela real sem mudar este fluxo."""
from __future__ import annotations

from . import demo
from . import placa as P
from .config import config
from .fontes.fipe import FipeFicticia
from .fontes.parceiro import obter
from .laudo import Item, Laudo, montar
from .regras import para_uf


class PlacaInvalida(ValueError):
    pass


def _itens_publicos(placa: str) -> list[Item]:
    multas = demo.multas_publicadas(placa)
    if multas:
        total = round(sum(m["valor"] for m in multas), 2)
        it_m = Item("multas_diario", "atencao", f"{len(multas)} multa(s) publicada(s) no Diário Oficial de Manaus",
                    "IMMU / Diário Oficial do Município", publico=True, valor=total)
    else:
        it_m = Item("multas_diario", "ok", "Nenhuma multa publicada", "IMMU / Diário Oficial do Município",
                    publico=True)
    lei = demo.leiloes_da_placa(placa)
    if lei:
        l0 = lei[0]
        it_l = Item("leilao_publico", "critico", f"Vendido em leilão público: {l0['orgao']} · {l0['data']} · "
                    f"{l0['condicao']}", "PNCP + editais do Detran-AM", publico=True)
    else:
        it_l = Item("leilao_publico", "ok", "Não aparece em leilões públicos", "PNCP + editais do Detran-AM",
                    publico=True)
    return [it_m, it_l]


def cadastro_e_fipe(placa: str) -> tuple[dict, dict]:
    p = P.normalizar(placa)
    if not P.valida(p):
        raise PlacaInvalida(placa)
    cadastro, _ = obter(config.parceiro).consultar(p)
    return cadastro, FipeFicticia().da_placa(p)


def laudo(placa: str, plano: str = "completa") -> tuple[Laudo, dict, dict]:
    p = P.normalizar(placa)
    if not P.valida(p):
        raise PlacaInvalida(placa)
    cadastro, itens = obter(config.parceiro).consultar(p)
    fipe = FipeFicticia().da_placa(p)
    l = montar(p, cadastro.get("uf") or "AM", plano, fipe["valor"], [*itens, *_itens_publicos(p)], cadastro)
    return l, cadastro, fipe


def resumo_ipva(cadastro: dict, valor_venal: float, anos_sem_multa: int = 0) -> dict | None:
    return para_uf(cadastro.get("uf")).ipva(valor_venal, cadastro.get("cilindrada"),
                                            moto=cadastro.get("tipo") == "moto", anos_sem_multa=anos_sem_multa)
