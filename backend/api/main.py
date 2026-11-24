"""API do Sonar Auto+ (FastAPI). Modo demonstração: dados fictícios, sem banco e sem login.

Rodar: uvicorn api.main:app --reload   →  http://localhost:8000/docs   (protótipo em http://localhost:8000/demo/)
Na AWS (Fase 1): o mesmo app na Lambda via Mangum, como no LIC; o plano vem do login (Cognito), não da URL.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sonar import __version__, demo, planos
from sonar import placa as P
from sonar.config import config
from sonar.consulta import PlacaInvalida, cadastro_e_fipe, laudo
from sonar.eventos import hoje
from sonar.laudo import para_dict
from sonar.servicos import compra, dono, leiloes, vender

app = FastAPI(title="Sonar Auto+", version=__version__,
              description="Consulta veicular pela placa — Brasil, começando pelo Amazonas. **Dados fictícios.**")
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origens, allow_methods=["*"], allow_headers=["*"])

PLANOS_VALIDOS = list(planos.PLANOS)


class UsoMemoria:
    """Limite de placas FIPE por dia em memória (só demonstração; produção usa eventos.consumir_fipe no banco).
    Mesma regra: placa repetida no dia não conta."""

    def __init__(self):
        self.vistas: dict[tuple, set] = defaultdict(set)
        self.contador: dict[str, set] = defaultdict(set)

    def consumir(self, chave: str, plano: str, placa: str) -> dict:
        k = (chave, hoje())
        limite = planos.limite_fipe(plano)
        if placa not in self.vistas[k]:
            if limite is not None and len(self.vistas[k]) >= limite:
                raise HTTPException(429, f"Limite de {limite} placas por dia no plano {planos.plano(plano)['nome']}")
            self.vistas[k].add(placa)
        self.contador[placa].add(chave)
        return {"usadas": len(self.vistas[k]), "limite": limite}


uso = UsoMemoria()


def _plano(p: str) -> str:
    if p not in PLANOS_VALIDOS:
        raise HTTPException(422, f"plano deve ser um de {PLANOS_VALIDOS}")
    return p


def _placa(p: str) -> str:
    n = P.normalizar(p)
    if not P.valida(n):
        raise HTTPException(422, "Placa inválida. Use ABC1D23 ou ABC1234.")
    return n


def _vezes(placa: str) -> int:
    return demo.veiculo(placa).get("consultas_30d", 0) + len(uso.contador[placa])


@app.get("/saude")
def saude():
    return {"ok": True, "versao": __version__, "parceiro": config.parceiro, "ufs_com_regras": config.ufs_regras,
            "dados": "fictícios"}


@app.get("/planos")
def listar_planos():
    return {k: {**v, "itens": sorted(v["itens"])} for k, v in planos.PLANOS.items()} | {"pacotes": planos.PACOTES}


@app.get("/placa/{placa}/fipe")
def fipe(placa: str, request: Request, plano: str = "visitante"):
    p, plano = _placa(placa), _plano(plano)
    limite = uso.consumir(request.client.host if request.client else "anonimo", plano, p)
    cadastro, f = cadastro_e_fipe(p)
    return {"placa": p, "modelo": cadastro["modelo"], "ano": cadastro["ano"], "tipo": cadastro["tipo"],
            "fipe": f, "consultada_30d": _vezes(p), "uso_hoje": limite,
            "aviso": "FIPE grátis, valor de tabela puro (sem ajuste por leilão)."}


@app.get("/placa/{placa}/laudo")
def obter_laudo(placa: str, plano: str = "completa", preco_pedido: float | None = Query(None, gt=0)):
    p, plano = _placa(placa), _plano(plano)
    try:
        l, cadastro, f = laudo(p, plano)
    except PlacaInvalida:
        raise HTTPException(422, "Placa inválida")
    d = para_dict(l, preco_pedido)
    d["veiculo"] = {k: cadastro.get(k) for k in ("modelo", "ano", "cor", "municipio", "uf", "tipo")}
    d["fipe_historico"] = f["historico"]
    d["consultada_30d"] = _vezes(p)
    d["proprietario"] = "oculto (LGPD)"
    return d


@app.get("/modelos")
def modelos():
    return demo.modelos()


@app.get("/minha-placa/{placa}/avisos")
def avisos(placa: str, anos_sem_multa: int = Query(0, ge=0, le=3)):
    return dono.avisos(_placa(placa), anos_sem_multa=anos_sem_multa)


@app.get("/leiloes")
def radar(plano: str = "visitante", uf: str = "AM"):
    return leiloes.radar(_plano(plano), uf)


@app.get("/vender/quanto-pedir")
def quanto_pedir(placa: str, estado: str = "bom"):
    try:
        return vender.quanto_pedir(_placa(placa), estado)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/comprar/transferencia")
def transferencia(despachante: bool = False):
    return compra.custo_transferencia(despachante)


@app.get("/comprar/custo-mensal/{placa}")
def custo_mensal(placa: str):
    return compra.custo_mensal(_placa(placa))


@app.get("/parceiros")
def parceiros():
    return demo.parceiros_comissao()


@app.get("/revenda/painel")
def painel_revenda():
    e = demo.estoque_revenda()
    linhas = []
    for pl in e["placas"]:
        l, cad, f = laudo(pl, "pro")
        n = l.nota()
        linhas.append({"placa": pl, "modelo": cad["modelo"], "fipe": f["valor"], "nota": n,
                       "situacao": "ok" if n >= 80 else "atencao" if n >= 50 else "critico",
                       "pontos_de_atencao": l.pontos_de_atencao})
    return {"revenda": e["revenda"], "placas": linhas, "total_placas": len(linhas),
            "com_alerta": sum(1 for x in linhas if x["situacao"] != "ok"),
            "valor_fipe_estoque": round(sum(x["fipe"] for x in linhas), 2)}


_PROTOTIPO = Path(__file__).resolve().parents[2] / "prototipo"
if _PROTOTIPO.exists():
    app.mount("/demo", StaticFiles(directory=_PROTOTIPO, html=True), name="demo")
