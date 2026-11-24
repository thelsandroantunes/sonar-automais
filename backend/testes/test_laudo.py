from sonar import planos
from sonar.laudo import Item, montar


def _itens():
    return [Item("roubo_furto", "ok", "", "parceiro"), Item("gravame", "atencao", "", "parceiro"),
            Item("leilao_privado", "critico", "", "parceiro"),
            Item("debitos", "critico", "", "parceiro", valor=1000.0)]


def test_nota_valor_justo_e_oferta_na_completa():
    l = montar("OAB7C89", "AM", "completa", 100000.0, _itens())
    assert l.item("zfm") is not None                    # regra do AM entrou sozinha
    assert l.nota() == round(100 - 7.5 - 25 - 8)        # gravame/2 + leilão + débitos
    vj = l.valor_justo()
    assert vj["desconto_leilao"] == 25000 and vj["valor_justo"] == 74000
    o = l.oferta(90000)
    assert o["oferta_sugerida"] == 70300 and o["economia"] == 19700


def test_plano_gratis_bloqueia_itens_e_nao_da_nota():
    l = montar("OAB7C89", "AM", "gratis", 100000.0, _itens())
    assert l.nota() is None and l.valor_justo() is None
    assert all(i.situacao == "bloqueado" for i in l.visiveis)
    assert l.pontos_de_atencao == 3


def test_essencial_tem_nota_sem_oferta():
    l = montar("PHX4E56", "SP", "essencial", 70000.0, _itens())
    assert l.nota() is not None and l.oferta(70000) is None
    assert l.item("zfm") is None                        # SP ainda sem pacote de regras


def test_limites_por_plano():
    assert planos.limite_fipe("visitante") == 10 and planos.limite_fipe("pro") is None
    assert planos.preco_laudo("completa", moto=True) == 24.90


def test_servicos_gratis_e_radar():
    assert planos.libera("gratis", "vigiar_placa") and planos.libera("gratis", "radar_leiloes")
    assert not planos.libera("visitante", "vigiar_placa")
    assert planos.atraso_radar("gratis") == 24 and planos.atraso_radar("pro") == 0
    assert planos.libera("completa", "quanto_pedir") and not planos.libera("essencial", "quanto_pedir")
