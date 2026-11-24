from sonar.fontes.editais_pdf import notificacoes_immu
from sonar.fontes.pncp_leiloes import registros


def test_notificacoes_immu():
    t = "EDITAL DE NOTIFICAÇÃO DE AUTUAÇÃO JWK-5658 MT01864090 554-1/2 28/10 EBR-8766 MT01547475 518-5/1 22/11"
    r = notificacoes_immu(t, 2024)
    assert [x["placa"] for x in r] == ["JWK5658", "EBR8766"] and r[0]["auto"] == "MT01864090"


def test_leilao_pncp_so_veiculo_com_placa():
    c = {"objetoCompra": "ALIENAÇÃO DOS SEGUINTES VEICULOS: UM CAMINHÃO IVECO - PLACA HLF 4845",
         "orgaoEntidade": {"razaoSocial": "MUNICIPIO X"}, "unidadeOrgao": {"ufSigla": "MG"},
         "modalidadeNome": "Leilão - Eletrônico", "dataPublicacaoPncp": "2026-11-10T10:00:00"}
    r = registros(c)
    assert len(r) == 1 and r[0]["placa"] == "HLF4845" and r[0]["data"] == "2026-11-10"
    assert registros({"objetoCompra": "Alienação de imóvel"}) == []
