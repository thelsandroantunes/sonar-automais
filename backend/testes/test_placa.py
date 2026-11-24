from sonar import placa as P


def test_valida_formatos():
    assert P.valida("abc-1234") and P.valida("QZA1B23")
    assert not P.valida("AB12345") and not P.valida("")


def test_equivalentes_antiga_mercosul():
    assert P.equivalentes("ABC1234") == {"ABC1234", "ABC1C34"}
    assert P.equivalentes("ABC1C34") == {"ABC1C34", "ABC1234"}


def test_placas_no_texto():
    t = "ALIENAÇÃO DOS SEGUINTES VEICULOS: UM CAMINHÃO IVECO - PLACA HLF 4845 ANO 2010; MOTO JWK-5658"
    assert P.no_texto(t) == ["HLF4845", "JWK5658"]
