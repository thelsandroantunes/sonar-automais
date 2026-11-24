"""Carrega os dados fictícios no PostgreSQL (usuário de teste, base pública fictícia e monitoramentos).

Uso: python -m coleta.migrar && python -m coleta.semear
"""
from __future__ import annotations

import json
import os

from sonar import demo
from sonar import placa as P
from sonar.db import conexao


def semear() -> dict:
    email = os.getenv("SEED_EMAIL", "teste@exemplo.com.br")
    n_pub = n_mon = 0
    with conexao() as conn:
        u = conn.execute("""INSERT INTO usuario (email, plano) VALUES (%s, 'pro')
                            ON CONFLICT (email) DO UPDATE SET plano = 'pro' RETURNING id""", (email,)).fetchone()
        for m in demo._ler("multas_diario_manaus.json")["registros"]:
            conn.execute("""INSERT INTO registro_publico (placa_hash, fonte, tipo, uf, orgao, data, detalhe)
                            VALUES (%s, 'immu_dom', 'multa_publicada', 'AM', 'IMMU', %s, %s) ON CONFLICT DO NOTHING""",
                         (P.hash_placa(m["placa"]), m["publicado_em"], json.dumps(m, ensure_ascii=False)))
            n_pub += 1
        for l in demo.leiloes():
            conn.execute("""INSERT INTO registro_publico (placa_hash, fonte, tipo, uf, orgao, data, detalhe)
                            VALUES (%s, %s, 'leilao_publico', %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                         (P.hash_placa(l["placa"]), l["fonte"], l["uf"], l["orgao"], l["data"],
                          json.dumps(l, ensure_ascii=False)))
            n_pub += 1
        for pl in demo.estoque_revenda()["placas"]:
            conn.execute("""INSERT INTO monitoramento (usuario_id, placa_hash, placa_mascarada)
                            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                         (u["id"], P.hash_placa(pl), pl[:4] + "•" + pl[5:]))
            n_mon += 1
    return {"usuario": email, "registros_publicos": n_pub, "monitoramentos": n_mon}


if __name__ == "__main__":
    from sonar.db import fechar_pool
    try:
        print(semear())
    finally:
        fechar_pool()
