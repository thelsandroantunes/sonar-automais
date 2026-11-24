"""Regras do Amazonas (onda 1).

IPVA 2026 (Sefaz-AM): alíquota reduzida — 1,5% para até 1.000 cc e para elétricos/híbridos; 2% acima de 1.000 cc
(conferir a tabela oficial da Sefaz-AM antes de produção). Desconto de bom condutor cumulativo com o antecipado:
10%, 15% ou 20% conforme os anos sem infração. Parcelamento em até 3 vezes.

Restrição tributária (Detran-AM, "Baixa de Restrição Tributária"): veículos comprados com isenção (IPI, ICMS, II) na
Zona Franca de Manaus ou em área de livre comércio têm restrição no prontuário; transferir para fora antes de 2 anos
(3 em alguns casos) exige autorização da Receita Federal e a baixa exige pagar o imposto.
"""
from __future__ import annotations

from datetime import date

from .nacional import RegrasNacionais

ALIQUOTA_ATE_1000 = 0.015
ALIQUOTA_ELETRICO = 0.015
ALIQUOTA_ACIMA_1000 = 0.02
ALIQUOTA_MOTO = 0.015          # conferir tabela Sefaz-AM
BOM_CONDUTOR = {1: 0.10, 2: 0.15, 3: 0.20}   # anos sem infração → desconto
PARCELAS_MAX = 3
PRAZO_RESTRICAO_ANOS = 2


class RegrasAM(RegrasNacionais):
    uf = "AM"
    tem_regras_locais = True

    def __init__(self):
        super().__init__("AM")

    def aliquota(self, cilindrada: int | None, eletrico: bool, moto: bool) -> float:
        if eletrico:
            return ALIQUOTA_ELETRICO
        if moto:
            return ALIQUOTA_MOTO
        if cilindrada is not None and cilindrada <= 1000:
            return ALIQUOTA_ATE_1000
        return ALIQUOTA_ACIMA_1000

    def ipva(self, valor_venal: float, cilindrada: int | None = None, eletrico: bool = False,
             anos_sem_multa: int = 0, moto: bool = False) -> dict:
        aliq = self.aliquota(cilindrada, eletrico, moto)
        bruto = round(valor_venal * aliq, 2)
        desc = BOM_CONDUTOR.get(min(anos_sem_multa, 3), 0.0)
        liquido = round(bruto * (1 - desc), 2)
        return {"uf": "AM", "aliquota": aliq, "valor_bruto": bruto, "desconto_bom_condutor": desc,
                "valor": liquido, "parcelas_max": PARCELAS_MAX, "parcela": round(liquido / PARCELAS_MAX, 2)}

    def restricao_tributaria(self, cadastro: dict) -> dict:
        """cadastro: {"restricao_tributaria": bool, "data_aquisicao": date|None} — vem do cadastro estadual (parceiro)."""
        if not cadastro.get("restricao_tributaria"):
            return {"aplica": False, "texto": "Sem restrição tributária da Zona Franca."}
        aquisicao = cadastro.get("data_aquisicao")
        texto = ("Comprado com isenção da Zona Franca: para levar a outro estado é preciso pagar o imposto e pedir a "
                 "baixa da restrição no Detran-AM.")
        dentro_prazo = None
        if isinstance(aquisicao, date):
            anos = (date.today() - aquisicao).days / 365.25
            dentro_prazo = anos < PRAZO_RESTRICAO_ANOS
            if dentro_prazo:
                texto += " Ainda dentro do prazo em que a Receita Federal precisa autorizar a transferência."
        return {"aplica": True, "texto": texto, "dentro_prazo": dentro_prazo,
                "passos": ["Receita Federal e/ou Sefaz-AM: calcular o imposto e obter a autorização",
                           "Laudo de vistoria no posto do Detran-AM (São Francisco)",
                           "Agendar e pagar a taxa de baixa no Detran-AM"]}

    def avisos(self, cadastro: dict) -> list[str]:
        out = []
        if cadastro.get("multas_publicadas_diario"):
            out.append("Há multa publicada no Diário Oficial de Manaus (a carta pode não ter chegado ao dono).")
        return out
