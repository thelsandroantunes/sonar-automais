# Sonar Auto+

Consulta veicular pela placa — Brasil, começando pelo **Amazonas com as regras do Amazonas** (Zona Franca, IPVA 2026,
multas publicadas no Diário Oficial de Manaus, leilões do Detran-AM). Nota 0–100 em semáforo, “quanto vale de verdade”
e “quanto oferecer”. Base técnica herdada do Radar Licita+ (`radar-licitamais`).

**Demonstração (GitHub Pages):** https://thelsandroantunes.github.io/sonar-automais/

> **Fase atual: demonstração com dados fictícios.** Placas, valores, multas e leilões em `dados-referencia/ficticios/`
> são inventados. Parceiro pago de dados ainda não escolhido (Fase 0).

## Estrutura
```
backend/
  sonar/                 regras de negócio
    planos.py              planos, limites e o que cada um libera (fonte única dos números)
    laudo.py               nota 0–100, veredito, valor justo, quanto oferecer
    consulta.py            orquestra FIPE + base pública + parceiro + regras da UF
    regras/                pacote de regras por UF: am.py (Zona Franca, IPVA AM) e nacional.py
    fontes/                fipe.py, pncp_leiloes.py, editais_pdf.py (IMMU, Detran-AM), parceiro.py
    servicos/              dono.py (vigiar a placa), leiloes.py (radar), vender.py, compra.py
    demo.py                leitura dos dados fictícios
    placa.py               validação, formatos antigo/Mercosul, placa em texto, hash (LGPD)
    pncp.py db.py config.py eventos.py visitantes.py alertas.py   (vindos do LIC)
  api/main.py            FastAPI (rotas em docs/api.md)
  coleta/                migrar.py, semear.py (dados fictícios no banco), coletar_leiloes_pncp.py
  migracoes/             SQL do PostgreSQL 16
  testes/                pytest (21 testes, sem banco)
dados-referencia/
  ficticios/             veículos, multas no Diário Oficial, leilões, taxas, estoque, parceiros (FICTÍCIOS)
  exemplos/              textos de edital para testar os leitores de PDF
prototipo/index.html     protótipo navegável (abre sozinho ou em /demo/ pela API)
infra/                   AWS CDK (pilhas Sonar*, vindas do LIC) e cópia dos workflows do GitHub
scripts/                 api.sh, testes.sh, banco.sh (Git Bash no Windows)
docs/                    plano estratégico, pesquisas, API, dados fictícios, reaproveitamento do LIC
```

## Rodar (Windows, Git Bash) — sem banco
```bash
bash scripts/api.sh        # http://localhost:8000/docs  ·  protótipo: http://localhost:8000/demo/
bash scripts/testes.sh     # 21 testes
```
Sem os scripts: `cd backend && python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt
&& uvicorn api.main:app --reload`.

## Com banco (opcional)
```bash
cp .env.example .env
bash scripts/banco.sh      # Docker: PostgreSQL 16 + migrações + dados fictícios no banco
```

## Experimente
- `GET /placa/OAB7C89/laudo?plano=completa&preco_pedido=118000` — crítico: leilão, busca e apreensão, Zona Franca
- `GET /placa/PHX4E56/laudo?plano=gratis` — o que o Grátis vê (itens bloqueados, “N pontos de atenção”)
- `GET /minha-placa/PHX4E56/avisos` — multa no Diário Oficial com prazo de defesa, IPVA, licenciamento
- `GET /leiloes?plano=pro` — radar de leilões públicos

## GitHub Actions e Pages
A pasta `.github` não pôde ser criada pelas ferramentas remotas: copie para `.github/workflows/`
`infra/github-workflows/testes.yml` (testes a cada envio) e `pages.yml` (demonstração). O `deploy.yml` (AWS) fica para a Fase 1.

GitHub Pages (uma vez): Settings → Pages → Build and deployment → Source: **GitHub Actions**. A cada envio que mexer em
`prototipo/`, o site é republicado em https://thelsandroantunes.github.io/sonar-automais/ (página marcada para não aparecer
no Google: `noindex`). Pages em repositório privado exige plano pago do GitHub.

## Documentos
`docs/plano-estrategico.md` · `docs/pesquisa-mercado.md` · `docs/pesquisa-amazonas.md` · `docs/api.md` ·
`docs/dados-ficticios.md` · `docs/reaproveitamento-lic.md` · `infra/LEIA-ME.md`
