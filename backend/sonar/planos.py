"""Planos, limites e itens do laudo por plano — fonte única dos números (mesmo padrão do LIC: licitamais/planos.py).

Preços são de referência (validar na Fase 0). Ids fixos no banco e no código; "nome" é o que aparece na tela.
"""
from __future__ import annotations

# itens do laudo (ordem da tela)
ITENS = ["fipe", "contador", "ipva_simulador", "antigolpe", "roubo_furto", "gravame", "renajud", "debitos",
         "multas_diario", "zfm", "leilao_publico", "leilao_privado", "busca_apreensao", "multas_federais", "recall", "nota",
         "valor_justo", "oferta", "compartilhar", "monitorar"]

# serviços além da placa (24/11/2026): dado público ou comissão, custo ~0 — entram cedo no teste
SERVICOS_GRATIS = {"fipe_modelo", "vigiar_placa", "calendario_ipva", "guia_zfm", "contrato_venda", "custo_transferencia",
                   "radar_leiloes", "pagar_debitos"}
_BASE_GRATIS = {"fipe", "contador", "fipe_modelo"}
_GRATIS = _BASE_GRATIS | {"ipva_simulador", "antigolpe"} | SERVICOS_GRATIS
_ESSENCIAL = _GRATIS | {"roubo_furto", "gravame", "renajud", "debitos", "multas_diario", "zfm", "leilao_publico", "nota"}
_COMPLETA = _ESSENCIAL | {"leilao_privado", "busca_apreensao", "multas_federais", "recall", "valor_justo", "oferta",
                          "compartilhar", "monitorar", "quanto_pedir"}

# radar de leilões: Grátis vê com atraso (mesma regra do LIC: ATRASO_HORAS); Pro e Empresa na hora, com alerta
ATRASO_RADAR_HORAS = {"visitante": 24, "gratis": 24}
VIGIAR_PLACAS = {"gratis": 1, "essencial": 1, "completa": 1, "pro": 50, "empresa": 300}

PLANOS = {
    "visitante": {"nome": "Visitante", "preco": 0, "cobranca": None, "fipe_dia": 10, "itens": _BASE_GRATIS,
                  "monitorar_placas": 0, "laudos_inclusos": 0, "adicional": None, "usuarios": 0},
    "gratis": {"nome": "Grátis", "preco": 0, "cobranca": None, "fipe_dia": 30, "itens": _GRATIS,
               "monitorar_placas": 0, "laudos_inclusos": 0, "adicional": None, "usuarios": 1},
    "essencial": {"nome": "Essencial", "preco": 19.90, "cobranca": "placa", "fipe_dia": 30, "itens": _ESSENCIAL,
                  "monitorar_placas": 0, "laudos_inclusos": 0, "adicional": None, "usuarios": 1},
    "completa": {"nome": "Completa", "preco": 39.90, "preco_moto": 24.90, "cobranca": "placa", "fipe_dia": 30,
                 "itens": _COMPLETA, "monitorar_placas": 1, "monitorar_dias": 30, "laudos_inclusos": 0,
                 "adicional": None, "usuarios": 1},
    "pro": {"nome": "Pro (revenda)", "preco": 199, "cobranca": "mes", "fipe_dia": None, "itens": _COMPLETA,
            "monitorar_placas": 50, "laudos_inclusos": 10, "adicional": 24.90, "usuarios": 3},
    "empresa": {"nome": "Empresa / API", "preco": 599, "cobranca": "mes", "fipe_dia": None, "itens": _COMPLETA,
                "monitorar_placas": 300, "laudos_inclusos": 40, "adicional": 19.90, "usuarios": None, "api": True},
}
PACOTES = {"procurando_carro": {"nome": "Procurando carro", "laudos": 3, "plano": "completa", "preco": 99}}


def plano(nome: str | None) -> dict:
    return PLANOS.get(nome or "visitante", PLANOS["visitante"])


def libera(nome_plano: str | None, item: str) -> bool:
    return item in plano(nome_plano)["itens"]


def limite_fipe(nome_plano: str | None) -> int | None:
    return plano(nome_plano)["fipe_dia"]


def preco_laudo(nome_plano: str, moto: bool = False) -> float:
    p = plano(nome_plano)
    return float(p.get("preco_moto") if moto and p.get("preco_moto") else p["preco"])


def atraso_radar(nome_plano: str | None) -> int:
    return ATRASO_RADAR_HORAS.get(nome_plano or "visitante", 0)
