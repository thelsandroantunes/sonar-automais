"""Aplica as migrações SQL pendentes (padrão do LIC). Uso: python -m coleta.migrar"""
from __future__ import annotations

from sonar.config import config
from sonar.db import conexao


def migrar() -> list[str]:
    feitas = []
    with conexao() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_versao (versao int PRIMARY KEY, "
                     "aplicada_em timestamptz NOT NULL DEFAULT now())")
        aplicadas = {r["versao"] for r in conn.execute("SELECT versao FROM schema_versao").fetchall()}
        for arq in sorted(config.migracoes.glob("*.sql")):
            v = int(arq.name.split("_")[0])
            if v in aplicadas:
                continue
            conn.execute(arq.read_text(encoding="utf-8"))
            feitas.append(arq.name)
    return feitas


if __name__ == "__main__":
    from sonar.db import fechar_pool
    try:
        print(migrar() or "nada a aplicar")
    finally:
        fechar_pool()
