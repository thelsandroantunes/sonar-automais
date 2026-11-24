from datetime import date

from sonar import demo
from sonar.servicos import dono, leiloes


def test_placa_desconhecida_vira_exemplo():
    v = demo.veiculo("ZZZ9Z99")
    assert v["placa"] == "ZZZ9Z99" and v["exemplo_de"] in {"QZA1B23", "PHX4E56", "OAB7C89", "QZB2E34"}


def test_prazo_de_defesa():
    a = dono.avisos("PHX4E56", hoje=date(2026, 11, 24))
    m = [x for x in a["avisos"] if x["tipo"] == "multa_publicada"]
    assert [x["dias_para_defesa"] for x in m] == [11, 0] and m[1]["prazo_vencido"]


def test_radar_ordena_futuros_primeiro():
    r = leiloes.radar("pro", hoje=date(2026, 11, 24))
    assert r["lotes"][0]["data"] == "2026-11-27" and r["lotes"][-1]["futuro"] is False
    assert next(l for l in r["lotes"] if l["lote"] == "45")["abaixo_fipe_pct"] == 60
