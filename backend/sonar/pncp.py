"""Cliente da API pública do PNCP.

Achados: erro 500 frequente (repetir resolve); 204 = vazio; tamanhoPagina 10–50;
/contratacoes/proposta não filtra por data de publicação (lista a UF toda); /contratacoes/publicacao filtra, mas
exige a modalidade (uma consulta por modalidade);
horários em Brasília sem fuso; não confiar em materialOuServico;
itens paginados (sem pagina/tamanhoPagina vêm só 10).
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from .config import config

BRASILIA = ZoneInfo("America/Sao_Paulo")
TAMANHO_PAGINA_ITENS = 500   # o endpoint de itens aceita páginas grandes
# modalidades com recebimento de proposta (a consulta por data de publicação exige a modalidade):
# 6 Pregão eletrônico · 8 Dispensa · 4 Concorrência eletrônica · 7 Pregão presencial · 5 Concorrência presencial ·
# 12 Credenciamento. Fora: leilão, concurso, diálogo competitivo, inexigibilidade, manifestação de interesse.
MODALIDADES_PROPOSTA = (6, 8, 4, 7, 5, 12)


class ErroPNCP(RuntimeError):
    """status = código HTTP da recusa (4xx); None = o PNCP não respondeu/fora do ar (5xx, rede) após as tentativas."""
    def __init__(self, msg: str, status: int | None = None):
        super().__init__(msg)
        self.status = status


class ClientePNCP:
    def __init__(self, cliente: httpx.Client | None = None, tentativas: int = 4, espera: float = 1.5):
        self.cli = cliente or httpx.Client(base_url=config.pncp_url, timeout=30,
                                           headers={"Accept": "application/json"})
        self.tentativas = tentativas
        self.espera = espera

    def _get(self, caminho: str, params: dict | None = None):
        ultimo = None
        for n in range(self.tentativas):
            try:
                r = self.cli.get(caminho, params=params)
                if r.status_code == 204:
                    return None
                if r.status_code == 200:
                    return r.json()
                if r.status_code < 500 and r.status_code != 429:
                    raise ErroPNCP(f"{r.status_code} em {caminho}: {r.text[:200]}", r.status_code)
                ultimo = f"HTTP {r.status_code}"
            except httpx.HTTPError as e:
                ultimo = repr(e)
            time.sleep(self.espera * (n + 1))
        raise ErroPNCP(f"Falhou após {self.tentativas} tentativas em {caminho}: {ultimo}")

    def propostas_abertas(self, uf: str, data_final: date | None = None, tamanho: int = 50):
        """Itera contratações com recebimento de proposta aberto na UF."""
        data_final = data_final or date(datetime.now(BRASILIA).year + 1, 12, 31)
        pagina = 1
        while True:
            d = self._get("/consulta/v1/contratacoes/proposta",
                          {"dataFinal": data_final.strftime("%Y%m%d"), "uf": uf,
                           "pagina": pagina, "tamanhoPagina": tamanho})
            if not d or not d.get("data"):
                return
            yield from d["data"]
            if pagina >= int(d.get("totalPaginas") or 1):
                return
            pagina += 1

    def publicadas(self, uf: str, dias: int, tamanho: int = 50, hoje: date | None = None,
                   modalidades: tuple[int, ...] = MODALIDADES_PROPOSTA):
        """Contratações PUBLICADAS na UF nos últimos `dias` dias (todas as modalidades com proposta), sem repetir.
        Bem mais rápido que listar todas as propostas abertas da UF (SP tem milhares): serve à coleta sob demanda.
        Quem chamar filtra as já encerradas."""
        hoje = hoje or datetime.now(BRASILIA).date()
        inicio = hoje - timedelta(days=max(1, dias) - 1)
        vistos: set[str] = set()
        for modalidade in modalidades:
            pagina = 1
            while True:
                d = self._get("/consulta/v1/contratacoes/publicacao",
                              {"dataInicial": inicio.strftime("%Y%m%d"), "dataFinal": hoje.strftime("%Y%m%d"),
                               "codigoModalidadeContratacao": modalidade, "uf": uf,
                               "pagina": pagina, "tamanhoPagina": tamanho})
                if not d or not d.get("data"):
                    break
                for c in d["data"]:
                    chave = c.get("numeroControlePNCP") or f"{(c.get('orgaoEntidade') or {}).get('cnpj')}-" \
                                                             f"{c.get('anoCompra')}-{c.get('sequencialCompra')}"
                    if chave not in vistos:
                        vistos.add(chave)
                        yield c
                if pagina >= int(d.get("totalPaginas") or 1):
                    break
                pagina += 1

    def itens(self, cnpj: str, ano: int, sequencial: int, tamanho: int = TAMANHO_PAGINA_ITENS) -> list[dict]:
        """Todos os itens. Sem 'pagina/tamanhoPagina' o PNCP devolve só os 10 primeiros (achado 20/11/2026)."""
        todos: list[dict] = []
        pagina = 1
        while True:
            d = self._get(f"/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens",
                          {"pagina": pagina, "tamanhoPagina": tamanho})
            lote = (d if isinstance(d, list) else (d or {}).get("data")) or []
            todos.extend(lote)
            if len(lote) < tamanho:
                return todos
            pagina += 1

    def resultados(self, cnpj: str, ano: int, sequencial: int, numero_item: int) -> list[dict]:
        """Resultado (vencedor e valor homologado) de UM item. Não há rota com os resultados de todos os itens de
        uma vez (testado em 22/11/2026: /itens/resultados = 400, /resultados = 404)."""
        d = self._get(f"/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numero_item}/resultados")
        return (d if isinstance(d, list) else (d or {}).get("data")) or []


def _data(v: str | None) -> datetime | None:
    if not v:
        return None
    dt = datetime.fromisoformat(v)
    return dt if dt.tzinfo else dt.replace(tzinfo=BRASILIA)


def converter_contratacao(c: dict) -> dict:
    orgao = c.get("orgaoEntidade") or {}
    unidade = c.get("unidadeOrgao") or {}
    cnpj = orgao.get("cnpj", "")
    return {
        "pncp_id": c.get("numeroControlePNCP") or f"{cnpj}-{c.get('anoCompra')}-{c.get('sequencialCompra')}",
        "orgao_cnpj": cnpj,
        "orgao_nome": orgao.get("razaoSocial") or unidade.get("nomeUnidade") or "",
        "ano": int(c.get("anoCompra")),
        "sequencial": int(c.get("sequencialCompra")),
        "uf": unidade.get("ufSigla"),
        "municipio": unidade.get("municipioNome"),
        "modalidade": c.get("modalidadeNome"),
        "objeto": c.get("objetoCompra") or "",
        "valor_estimado": c.get("valorTotalEstimado"),
        "abertura_proposta": _data(c.get("dataAberturaProposta")),
        "encerramento_proposta": _data(c.get("dataEncerramentoProposta")),
        "link_origem": c.get("linkSistemaOrigem"),
        "situacao": c.get("situacaoCompraNome"),
        "srp": c.get("srp"),
    }


def converter_item(i: dict) -> dict:
    return {
        "numero": int(i.get("numeroItem")),
        "descricao": i.get("descricao") or "",
        "catmat": str(i["catalogoCodigoItem"]) if i.get("catalogoCodigoItem") else None,
        "quantidade": i.get("quantidade"),
        "unidade": i.get("unidadeMedida"),
        "valor_unitario": i.get("valorUnitarioEstimado"),
        "valor_total": i.get("valorTotal"),
        "sigiloso": bool(i.get("orcamentoSigiloso")),
    }


def link_pncp(edital: dict) -> str:
    """Página PÚBLICA do edital no PNCP (abre sem login, com a aba "Arquivos").

    22/11/2026: o botão do site usava o linkSistemaOrigem (Licitanet, BLL, Compras.gov…), que costuma exigir login
    ou responder 403 — o cliente caía em outro site. Agora o link principal é sempre o do PNCP."""
    return f"https://pncp.gov.br/app/editais/{edital['orgao_cnpj']}/{edital['ano']}/{edital['sequencial']}"


# ------------------------------------------------------------------ documentos (PDF do edital, termo de referência…)
PNCP_ARQUIVOS = "https://pncp.gov.br/pncp-api/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos/{n}"
ROTA_DOCUMENTOS = re.compile(r"^(?:/api)?/pncp/documentos/(\d{14})/(\d{4})/(\d{1,9})/?$")
_ORDEM_TIPO = ("edital", "termo de refer", "aviso", "estudo", "minuta", "anexo")


def _peso_tipo(tipo: str) -> int:
    t = (tipo or "").lower()
    return next((i for i, p in enumerate(_ORDEM_TIPO) if p in t), len(_ORDEM_TIPO))


def converter_documento(d: dict, cnpj: str, ano: int, seq: int) -> dict | None:
    """Um arquivo da contratação no PNCP → {titulo, tipo, data, url}. None se estiver inativo/sem número."""
    if d.get("statusAtivo") is False:
        return None
    n = d.get("sequencialDocumento")
    url = d.get("url") or d.get("uri")
    if not url and n is None:
        return None
    if not url or not str(url).startswith("https://pncp.gov.br/"):
        url = PNCP_ARQUIVOS.format(cnpj=cnpj, ano=ano, seq=seq, n=n)
    tipo = d.get("tipoDocumentoNome") or d.get("tipoDocumentoDescricao") or "Documento"
    return {"titulo": (d.get("titulo") or tipo).strip(), "tipo": tipo, "data": d.get("dataPublicacaoPncp"),
            "url": url}


def documentos(cnpj: str, ano: int, seq: int, cliente: "ClientePNCP | None" = None) -> dict:
    """Arquivos públicos da contratação (edital em PDF, termo de referência, anexos), o edital primeiro.
    PNCP fora do ar não vira erro: {"documentos": [], "indisponivel": True, "pncp_fora": True} — a tela avisa que o
    problema é no PNCP (não no Radar) e, para quem paga, a borda serve a cópia guardada (licitamais/copia_docs.py).
    Recusa do PNCP (4xx, ex.: compra sem arquivos) = lista vazia, não "fora do ar"."""
    pagina = link_pncp({"orgao_cnpj": cnpj, "ano": ano, "sequencial": seq})
    cli = cliente or ClientePNCP(httpx.Client(base_url=config.pncp_url, timeout=8,
                                              headers={"Accept": "application/json"}), tentativas=2, espera=0.5)
    try:
        d = cli._get(f"/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos")
    except ErroPNCP as e:
        if e.status is not None:
            return {"documentos": [], "indisponivel": False, "pncp_fora": False, "pagina": pagina}
        return {"documentos": [], "indisponivel": True, "pncp_fora": True, "pagina": pagina}
    lista = d if isinstance(d, list) else ((d or {}).get("data") or [])
    docs = [x for x in (converter_documento(i, cnpj, ano, seq) for i in lista) if x]
    docs.sort(key=lambda x: (_peso_tipo(x["tipo"]), x["data"] or ""))
    return {"documentos": docs, "indisponivel": False, "pncp_fora": False, "pagina": pagina}


# situação do item no PNCP (situacaoCompraItem): 1 Em andamento · 2 Homologado · 3 Anulado/Revogado/Cancelado ·
# 4 Deserto · 5 Fracassado. Amostra do AM (mai–jun/2026): muitos "Fracassado", "Deserto" raro.
ITEM_HOMOLOGADO, ITEM_CANCELADO, ITEM_DESERTO, ITEM_FRACASSADO = 2, 3, 4, 5
SITUACOES_FINAIS = {ITEM_HOMOLOGADO, ITEM_CANCELADO, ITEM_DESERTO, ITEM_FRACASSADO}


def converter_item_historico(i: dict) -> dict:
    return {
        "numero": int(i.get("numeroItem")),
        "descricao": i.get("descricao") or "",
        "situacao": int(i["situacaoCompraItem"]) if i.get("situacaoCompraItem") is not None else None,
        "tem_resultado": bool(i.get("temResultado")),
        "valor_unit_estimado": i.get("valorUnitarioEstimado"),
        "unidade": (i.get("unidadeMedida") or None) and str(i.get("unidadeMedida"))[:40],   # 023 (23/11/2026)
    }


def vencedor(resultados: list[dict]) -> dict | None:
    """O resultado válido do item (sem cancelamento), o de menor sequencial. None se não houver."""
    validos = [r for r in resultados if not r.get("dataCancelamento")]
    if not validos:
        return None
    r = min(validos, key=lambda x: x.get("sequencialResultado") or 0)
    return {"valor_unit_homologado": r.get("valorUnitarioHomologado"), "fornecedor_ni": r.get("niFornecedor"),
            "fornecedor_porte": r.get("porteFornecedorNome"), "fornecedor_nome": r.get("nomeRazaoSocialFornecedor")}
