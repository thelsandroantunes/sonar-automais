"""Para quem compra: custo da transferência no Detran-AM e custo de ter o carro por mês (valores fictícios)."""
from __future__ import annotations

from .. import demo
from ..consulta import cadastro_e_fipe, resumo_ipva

SEGURO_PCT_ANO = 0.047      # fictício: % da FIPE por ano
MANUTENCAO_MES = 150.0      # fictício
COMBUSTIVEL_MES = {"carro": 600.0, "moto": 180.0}


def custo_transferencia(com_despachante: bool = False) -> dict:
    t = demo.taxas_detran_am()
    itens = dict(t["transferencia"])
    if com_despachante:
        itens["despachante"] = t["despachante_medio"]
    return {"uf": "AM", "itens": itens, "total": round(sum(itens.values()), 2), "aviso": t["_aviso"]}


def custo_mensal(placa: str) -> dict:
    cadastro, fipe = cadastro_e_fipe(placa)
    ipva = resumo_ipva(cadastro, fipe["valor"]) or {"valor": 0}
    tipo = cadastro.get("tipo") or "carro"
    itens = {"combustivel": COMBUSTIVEL_MES[tipo], "seguro": round(fipe["valor"] * SEGURO_PCT_ANO / 12, 2),
             "manutencao": MANUTENCAO_MES if tipo == "carro" else 60.0, "ipva": round(ipva["valor"] / 12, 2)}
    return {"placa": cadastro["placa"], "modelo": cadastro["modelo"], "itens": itens,
            "total_mes": round(sum(itens.values()), 2), "aviso": "Valores fictícios de demonstração."}
