"""Monta o laudo: itens por fonte, nota 0–100, "quanto vale de verdade" e "quanto oferecer".

Cada item guarda a situação ("ok" | "atencao" | "critico" | "indisponivel" | "bloqueado") e a fonte, para nunca mostrar
"nada consta" quando a fonte falhou (lição do LIC: dado ausente ≠ dado negativo).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import planos
from .regras import para_uf

# quanto cada problema tira da nota (atenção tira metade)
PESO = {"roubo_furto": 25, "busca_apreensao": 30, "leilao_privado": 25, "leilao_publico": 10, "gravame": 15,
        "renajud": 20, "debitos": 8, "multas_diario": 3, "multas_federais": 4, "zfm": 6, "recall": 3}
DESCONTO_LEILAO = 0.25        # carro com passagem por leilão costuma valer 20–30% abaixo da FIPE
MARGEM_NEGOCIACAO = 0.05      # oferta sugerida = valor justo − 5%


@dataclass
class Item:
    id: str
    situacao: str
    texto: str
    fonte: str
    publico: bool = False         # True = base própria/dado aberto (custo ~0)
    valor: float = 0.0            # débitos em R$


@dataclass
class Laudo:
    placa: str
    uf: str
    plano: str
    fipe: float | None
    itens: list[Item] = field(default_factory=list)

    def item(self, id_: str) -> Item | None:
        return next((i for i in self.itens if i.id == id_), None)

    @property
    def visiveis(self) -> list[Item]:
        return [i if planos.libera(self.plano, i.id) else Item(i.id, "bloqueado", "", i.fonte, i.publico)
                for i in self.itens]

    @property
    def pontos_de_atencao(self) -> int:
        return sum(1 for i in self.itens if i.situacao in ("atencao", "critico"))

    def nota(self) -> int | None:
        if not planos.libera(self.plano, "nota"):
            return None
        n = 100.0
        for i in self.itens:
            if not planos.libera(self.plano, i.id):
                continue
            peso = PESO.get(i.id, 0)
            n -= peso if i.situacao == "critico" else peso / 2 if i.situacao == "atencao" else 0
        return max(5, round(n))

    def veredito(self) -> str | None:
        n = self.nota()
        if n is None:
            return None
        return "pode_seguir" if n >= 80 else "negocie" if n >= 50 else "nao_compre"

    def debitos_total(self) -> float:
        return round(sum(i.valor for i in self.itens
                         if i.id in ("debitos", "multas_diario", "multas_federais") and planos.libera(self.plano, i.id)), 2)

    def valor_justo(self) -> dict | None:
        """Escada: FIPE → desconto de leilão → débitos → valor justo."""
        if self.fipe is None or not planos.libera(self.plano, "valor_justo"):
            return None
        leilao = any(i.id in ("leilao_privado", "leilao_publico") and i.situacao == "critico" for i in self.itens)
        desc = round(self.fipe * DESCONTO_LEILAO, 2) if leilao else 0.0
        deb = self.debitos_total()
        return {"fipe": self.fipe, "desconto_leilao": desc, "debitos": deb,
                "valor_justo": round(self.fipe - desc - deb, 2)}

    def oferta(self, preco_pedido: float) -> dict | None:
        vj = self.valor_justo()
        if vj is None:
            return None
        sugerida = round(vj["valor_justo"] * (1 - MARGEM_NEGOCIACAO), 2)
        return {"pedido": preco_pedido, "valor_justo": vj["valor_justo"], "oferta_sugerida": sugerida,
                "economia": round(max(0.0, preco_pedido - sugerida), 2),
                "acima_do_justo": round(preco_pedido - vj["valor_justo"], 2)}


def montar(placa: str, uf: str, plano: str, fipe: float | None, itens: list[Item], cadastro: dict | None = None
           ) -> Laudo:
    """Junta os itens das fontes com as regras da UF (ex.: ZFM no AM)."""
    regras = para_uf(uf)
    cadastro = cadastro or {}
    if regras.tem_regras_locais and not any(i.id == "zfm" for i in itens):
        r = regras.restricao_tributaria(cadastro)
        itens = [*itens, Item("zfm", "atencao" if r["aplica"] else "ok", r.get("texto", ""), "Detran-AM (cadastro)")]
    return Laudo(placa=placa, uf=uf.upper(), plano=plano, fipe=fipe, itens=itens)


def para_dict(l: Laudo, preco_pedido: float | None = None) -> dict:
    """Formato da API: itens bloqueados saem sem texto; nada de dado do proprietário (LGPD)."""
    return {"placa": l.placa, "uf": l.uf, "plano": l.plano, "fipe": l.fipe, "nota": l.nota(), "veredito": l.veredito(),
            "pontos_de_atencao": l.pontos_de_atencao, "debitos_total": l.debitos_total(),
            "valor_justo": l.valor_justo(), "oferta": l.oferta(preco_pedido) if preco_pedido else None,
            "itens": [{"id": i.id, "situacao": i.situacao, "texto": i.texto, "fonte": i.fonte, "publico": i.publico,
                       "valor": i.valor} for i in l.visiveis]}
