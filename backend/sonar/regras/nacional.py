"""Regras válidas em todo o Brasil (UF ainda sem pacote próprio)."""
from __future__ import annotations


class RegrasNacionais:
    uf = None
    tem_regras_locais = False
    # áreas de livre comércio usam a mesma lógica da ZFM (onda 2): RR, AP, AC, RO
    ufs_beneficio_tributario: set[str] = set()

    def __init__(self, uf: str | None = None):
        self.uf = uf

    def ipva(self, valor_venal: float, cilindrada: int | None = None, eletrico: bool = False,
             anos_sem_multa: int = 0, moto: bool = False) -> dict | None:
        """Sem tabela da UF: não simula (o laudo mostra só se está pago ou em atraso)."""
        return None

    def restricao_tributaria(self, cadastro: dict) -> dict:
        return {"aplica": False}

    def avisos(self, cadastro: dict) -> list[str]:
        return []
