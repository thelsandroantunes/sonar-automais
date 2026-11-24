"""Interface do parceiro pago (roubo/furto, gravame, RENAJUD, leilão privado, débitos, RENAINF).

A Fase 0 escolhe o fornecedor (APIBrasil, Consultar Placa, AnyCar ou ZapCar). Até lá: ParceiroFicticio, que lê
dados-referencia/ficticios/veiculos.json. Todo parceiro devolve (cadastro, itens) no mesmo formato.
"""
from __future__ import annotations

from .. import demo
from ..laudo import Item

ITENS_PARCEIRO = ("roubo_furto", "gravame", "renajud", "debitos", "leilao_privado", "busca_apreensao",
                  "multas_federais", "recall")
_SITUACAO = {"ok": "ok", "atencao": "atencao", "critico": "critico"}


class ParceiroFicticio:
    nome = "ficticio"

    def consultar(self, placa: str) -> tuple[dict, list[Item]]:
        v = demo.veiculo(placa)
        cadastro = {k: v.get(k) for k in ("placa", "tipo", "modelo", "ano", "cor", "municipio", "uf", "cilindrada",
                                          "codigo_fipe", "final_placa", "restricao_tributaria")}
        cadastro["data_aquisicao"] = demo.data_iso(v.get("data_aquisicao"))
        d = v["debitos"]
        itens = []
        for id_ in ITENS_PARCEIRO:
            sit, texto = v["parceiro"][id_]
            valor = 0.0
            if id_ == "debitos":
                valor = d["ipva"] + d["licenciamento"] + d["multas_estaduais"]
            if id_ == "multas_federais":
                valor = d["multas_federais"]
            itens.append(Item(id_, _SITUACAO[sit], texto, "parceiro (fictício)", valor=round(valor, 2)))
        return cadastro, itens


def obter(nome: str):
    if nome == "ficticio":
        return ParceiroFicticio()
    raise NotImplementedError(f"parceiro {nome!r}: implementar na Fase 0 após a cotação")
