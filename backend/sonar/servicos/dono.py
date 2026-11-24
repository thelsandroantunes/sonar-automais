"""“Vigiar a minha placa”: avisos para o dono — multa publicada no Diário Oficial (com prazo de defesa), IPVA,
licenciamento, recall e Zona Franca. Só dado público (Grátis: 1 placa; Pro: 50; Empresa: 300)."""
from __future__ import annotations

from datetime import date

from .. import demo
from ..consulta import cadastro_e_fipe, resumo_ipva
from ..regras import para_uf


def avisos(placa: str, hoje: date | None = None, anos_sem_multa: int = 0) -> dict:
    hoje = hoje or date.today()
    cadastro, fipe = cadastro_e_fipe(placa)
    v = demo.veiculo(placa)
    taxas = demo.taxas_detran_am()
    out = []
    for m in demo.multas_publicadas(placa):
        prazo = date.fromisoformat(m["prazo_defesa"])
        dias = (prazo - hoje).days
        out.append({"tipo": "multa_publicada", "nivel": "atencao" if dias >= 0 else "info",
                    "texto": f"Multa publicada no Diário Oficial de Manaus em {m['publicado_em']}: {m['descricao']}, "
                             f"R$ {m['valor']:.2f}",
                    "prazo_defesa": m["prazo_defesa"], "dias_para_defesa": max(dias, 0), "prazo_vencido": dias < 0,
                    "auto": m["auto"]})
    ipva = resumo_ipva(cadastro, fipe["valor"], anos_sem_multa)
    if ipva:
        out.append({"tipo": "ipva", "nivel": "info", "texto": f"IPVA 2027 cota única ≈ R$ {ipva['valor']:.2f}",
                    "vencimento": taxas["ipva_cota_unica_vencimento"], "ipva": ipva})
    lic = taxas["licenciamento_por_final"].get(str(cadastro.get("final_placa")))
    if lic:
        out.append({"tipo": "licenciamento", "nivel": "info", "texto": f"Licenciamento 2027 vence em {lic}",
                    "vencimento": lic})
    sit, txt = v["parceiro"]["recall"]
    if sit != "ok":
        out.append({"tipo": "recall", "nivel": "atencao", "texto": txt})
    zfm = para_uf(cadastro.get("uf")).restricao_tributaria(cadastro)
    out.append({"tipo": "zona_franca", "nivel": "atencao" if zfm.get("aplica") else "ok",
                "texto": zfm.get("texto", "Sem regra local para esta UF")})
    return {"placa": cadastro["placa"], "modelo": cadastro["modelo"], "avisos": out}
