from datetime import date, timedelta

from sonar.regras import para_uf
from sonar.regras.am import RegrasAM


def test_am_tem_regras_e_outra_uf_usa_nacional():
    assert para_uf("am").tem_regras_locais
    assert not para_uf("SP").tem_regras_locais
    assert para_uf("SP").ipva(50000) is None


def test_ipva_am_aliquota_e_bom_condutor():
    r = RegrasAM().ipva(60000, cilindrada=1000)
    assert r["aliquota"] == 0.015 and r["valor"] == 900.0
    r = RegrasAM().ipva(100000, cilindrada=2000, anos_sem_multa=3)
    assert r["valor_bruto"] == 2000.0 and r["valor"] == 1600.0 and r["parcela"] == round(1600 / 3, 2)


def test_restricao_zfm():
    assert RegrasAM().restricao_tributaria({})["aplica"] is False
    r = RegrasAM().restricao_tributaria({"restricao_tributaria": True,
                                          "data_aquisicao": date.today() - timedelta(days=200)})
    assert r["aplica"] and r["dentro_prazo"] and len(r["passos"]) == 3
