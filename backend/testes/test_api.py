from fastapi.testclient import TestClient

from api.main import app

c = TestClient(app)


def test_saude_e_planos():
    assert c.get("/saude").json()["dados"] == "fictícios"
    p = c.get("/planos").json()
    assert p["completa"]["preco"] == 39.90 and "vigiar_placa" in p["gratis"]["itens"]


def test_fipe_gratis_e_placa_invalida():
    r = c.get("/placa/phx-4e56/fipe").json()
    assert r["placa"] == "PHX4E56" and r["fipe"]["valor"] == 71430 and r["consultada_30d"] >= 11
    assert c.get("/placa/123/fipe").status_code == 422


def test_limite_visitante_e_placa_repetida():
    cli = TestClient(app, client=("10.0.0.9", 50000))
    for i in range(10):
        assert cli.get(f"/placa/AAA{1000 + i}/fipe").status_code == 200
    assert cli.get("/placa/AAA1000/fipe").status_code == 200       # repetida não conta
    assert cli.get("/placa/AAA2000/fipe").status_code == 429       # 11ª placa nova


def test_laudo_por_plano():
    comp = c.get("/placa/OAB7C89/laudo", params={"plano": "completa", "preco_pedido": 118000}).json()
    assert comp["nota"] < 50 and comp["veredito"] == "nao_compre" and comp["oferta"]["economia"] > 0
    assert any(i["id"] == "zfm" and i["situacao"] == "atencao" for i in comp["itens"])
    assert comp["proprietario"] == "oculto (LGPD)"
    gr = c.get("/placa/OAB7C89/laudo", params={"plano": "gratis"}).json()
    assert gr["nota"] is None and all(i["situacao"] == "bloqueado" for i in gr["itens"])


def test_servicos():
    a = c.get("/minha-placa/PHX4E56/avisos").json()
    assert {x["tipo"] for x in a["avisos"]} >= {"multa_publicada", "ipva", "licenciamento", "recall", "zona_franca"}
    r = c.get("/leiloes", params={"plano": "gratis"}).json()
    assert r["atraso_horas"] == 24 and len(r["lotes"]) == 5
    assert c.get("/leiloes", params={"plano": "pro"}).json()["alerta_na_hora"]
    q = c.get("/vender/quanto-pedir", params={"placa": "PHX4E56", "estado": "otimo"}).json()
    assert q["anuncie_por"] > q["fipe"] > q["vender_rapido"] - 5000
    assert c.get("/comprar/transferencia", params={"despachante": True}).json()["total"] == 730.70
    assert c.get("/revenda/painel").json()["total_placas"] == 6
