"""Coleta leilões públicos de veículos no PNCP e grava na base própria (registro_publico).

Uso: python -m coleta.coletar_leiloes_pncp [--uf AM] [--dias 30] [--seco]
--seco: não grava; só imprime as placas encontradas (útil sem banco).
"""
from __future__ import annotations

import argparse
import json

from sonar import placa as P
from sonar.fontes.pncp_leiloes import MODALIDADES_LEILAO, janela, registros
from sonar.pncp import ClientePNCP


def coletar(uf: str | None, dias: int) -> list[dict]:
    cli = ClientePNCP()
    ini, fim = janela(dias)
    achados: list[dict] = []
    for mod in MODALIDADES_LEILAO:
        pagina = 1
        while True:
            params = {"dataInicial": ini.strftime("%Y%m%d"), "dataFinal": fim.strftime("%Y%m%d"),
                      "codigoModalidadeContratacao": mod, "pagina": pagina, "tamanhoPagina": 50}
            if uf:
                params["uf"] = uf
            d = cli._get("/consulta/v1/contratacoes/publicacao", params)
            if not d or not d.get("data"):
                break
            for c in d["data"]:
                achados.extend(registros(c))
            if pagina >= int(d.get("totalPaginas") or 1):
                break
            pagina += 1
    return achados


def gravar(achados: list[dict]) -> int:
    from sonar.db import conexao
    n = 0
    with conexao() as conn:
        for a in achados:
            conn.execute("""INSERT INTO registro_publico (placa_hash, fonte, tipo, uf, orgao, data, detalhe, url)
                            VALUES (%s, 'pncp', 'leilao_publico', %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                         (P.hash_placa(a["placa"]), a["uf"], a["orgao"], a["data"] or None,
                          json.dumps({"modalidade": a["modalidade"]}), a["url"]))
            n += 1
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--uf")
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--seco", action="store_true")
    a = ap.parse_args()
    r = coletar(a.uf, a.dias)
    print(f"{len(r)} placas em leilões públicos")
    if a.seco:
        for x in r[:50]:
            print(x["uf"], x["placa"], x["orgao"], x["data"])
    else:
        from sonar.db import fechar_pool
        try:
            print(f"{gravar(r)} gravadas")
        finally:
            fechar_pool()
