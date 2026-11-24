"""Pacotes de regras por UF. O núcleo do laudo é nacional; cada UF da onda ativa acrescenta suas regras.

Para ligar uma UF nova: criar regras/<uf>.py com uma classe que herda RegrasNacionais e registrar em REGRAS.
"""
from __future__ import annotations

from ..config import config
from .am import RegrasAM
from .nacional import RegrasNacionais

REGRAS = {"AM": RegrasAM}


def para_uf(uf: str | None):
    uf = (uf or "").upper()
    if uf in REGRAS and uf in config.ufs_regras:
        return REGRAS[uf]()
    return RegrasNacionais(uf)
