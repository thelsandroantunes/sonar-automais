"""Placa: validação, normalização e hash (LGPD: registros de uso guardam só o hash)."""
from __future__ import annotations

import hashlib
import re

from .config import config

_ANTIGA = re.compile(r"^[A-Z]{3}[0-9]{4}$")
_MERCOSUL = re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$")
# dentro de textos de diário oficial/edital: "HLF 4845", "JWK-5658", "QZA1B23"
EM_TEXTO = re.compile(r"\b([A-Z]{3})[\s-]?([0-9][A-Z0-9][0-9]{2})\b")
# palavras de 3 letras comuns antes de números em editais ("ANO 2010", "LEI 1234"): não são placa
NAO_PLACA = {"ANO", "LEI", "CEP", "ART", "MOD", "NUM", "KMS", "POT", "CIL", "LOT", "COD", "REF", "PAG", "DEC", "INC"}
_MERCOSUL_LETRA = "ABCDEFGHIJ"  # 2º dígito da placa antiga vira letra na Mercosul (0=A … 9=J)


def normalizar(placa: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (placa or "").upper())


def valida(placa: str | None) -> bool:
    p = normalizar(placa)
    return bool(_ANTIGA.match(p) or _MERCOSUL.match(p))


def equivalentes(placa: str) -> set[str]:
    """A mesma placa nos dois formatos (ABC1234 ↔ ABC1C34): leilões antigos citam a placa antiga."""
    p = normalizar(placa)
    if _ANTIGA.match(p):
        return {p, p[:4] + _MERCOSUL_LETRA[int(p[4])] + p[5:]}
    if _MERCOSUL.match(p) and p[4] in _MERCOSUL_LETRA:
        return {p, p[:4] + str(_MERCOSUL_LETRA.index(p[4])) + p[5:]}
    return {p}


def no_texto(texto: str) -> list[str]:
    """Placas citadas num texto livre (objeto de leilão, edital de notificação), sem repetir, na ordem."""
    vistos: list[str] = []
    for a, b in EM_TEXTO.findall((texto or "").upper()):
        p = a + b
        if a in NAO_PLACA:
            continue
        if valida(p) and p not in vistos:
            vistos.append(p)
    return vistos


def hash_placa(placa: str) -> str:
    return hashlib.sha256(f"{config.sal_hash}:{normalizar(placa)}".encode()).hexdigest()[:32]
