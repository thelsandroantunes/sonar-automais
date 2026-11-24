-- Sonar Auto+ — esquema inicial (PostgreSQL 16). Padrão do LIC: SQL explícito, sem ORM.
CREATE TABLE IF NOT EXISTS schema_versao (versao int PRIMARY KEY, aplicada_em timestamptz NOT NULL DEFAULT now());

CREATE TABLE usuario (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  plano text NOT NULL DEFAULT 'gratis' CHECK (plano IN ('gratis','pro','empresa')),
  uf text NOT NULL DEFAULT 'AM',
  criado_em timestamptz NOT NULL DEFAULT now()
);

-- visitante sem cadastro (copiado do LIC, migração 002)
CREATE TABLE visitante (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  impressao text NOT NULL, ip_hash text,
  criado_em timestamptz NOT NULL DEFAULT now(), ultimo_acesso timestamptz NOT NULL DEFAULT now(),
  usuario_id uuid REFERENCES usuario(id)
);
CREATE INDEX ON visitante (impressao, ultimo_acesso DESC);

-- limite diário (copiado do LIC) e placas consultadas (contador da placa; só hash — LGPD)
CREATE TABLE uso_diario (chave text NOT NULL, dia date NOT NULL, buscas int NOT NULL DEFAULT 0,
                         PRIMARY KEY (chave, dia));
CREATE TABLE consulta_placa (chave text NOT NULL, placa_hash text NOT NULL, dia date NOT NULL,
                             PRIMARY KEY (chave, placa_hash, dia));
CREATE INDEX ON consulta_placa (placa_hash, dia);

-- laudos comprados (avulso ou por plano) e itens com a fonte de cada um
CREATE TABLE laudo (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id uuid REFERENCES usuario(id),
  placa_hash text NOT NULL, placa_mascarada text NOT NULL,   -- ex.: PHX4•56
  uf text NOT NULL, tipo text NOT NULL CHECK (tipo IN ('essencial','completa')),
  nota int, fipe numeric(12,2), valor_justo numeric(12,2),
  link_publico text UNIQUE,                                    -- "vendedor verificado"
  criado_em timestamptz NOT NULL DEFAULT now(), valido_ate timestamptz NOT NULL DEFAULT now() + interval '24 hours'
);
CREATE TABLE laudo_item (
  laudo_id uuid REFERENCES laudo(id) ON DELETE CASCADE, item text NOT NULL,
  situacao text NOT NULL CHECK (situacao IN ('ok','atencao','critico','indisponivel')),
  texto text, fonte text NOT NULL, publico boolean NOT NULL DEFAULT false, valor numeric(12,2) DEFAULT 0,
  PRIMARY KEY (laudo_id, item)
);

-- base própria de dados públicos: uma linha por placa citada numa fonte aberta
CREATE TABLE registro_publico (
  id bigserial PRIMARY KEY,
  placa_hash text NOT NULL,
  fonte text NOT NULL,          -- pncp | detran_am_leilao | detran_am_resenha | immu_dom | doe_am | querido_diario
  tipo text NOT NULL,           -- leilao_publico | patio | multa_publicada
  uf text, orgao text, data date, detalhe jsonb NOT NULL DEFAULT '{}', url text,
  coletado_em timestamptz NOT NULL DEFAULT now(),
  UNIQUE (placa_hash, fonte, tipo, data, detalhe)
);
CREATE INDEX ON registro_publico (placa_hash);

-- coletas por fonte e UF (padrão coleta_uf do LIC)
CREATE TABLE coleta_fonte (fonte text NOT NULL, uf text NOT NULL, ultima_coleta timestamptz, registros int DEFAULT 0,
                           erro text, PRIMARY KEY (fonte, uf));

-- monitoramento de placa e alertas (adaptado de preferencia_alerta/alerta do LIC)
CREATE TABLE monitoramento (
  id bigserial PRIMARY KEY, usuario_id uuid NOT NULL REFERENCES usuario(id),
  placa_hash text NOT NULL, placa_mascarada text NOT NULL, apelido text,
  ativo boolean NOT NULL DEFAULT true, ate timestamptz, criado_em timestamptz NOT NULL DEFAULT now(),
  UNIQUE (usuario_id, placa_hash)
);
CREATE TABLE alerta (
  id bigserial PRIMARY KEY, usuario_id uuid NOT NULL REFERENCES usuario(id),
  monitoramento_id bigint NOT NULL REFERENCES monitoramento(id) ON DELETE CASCADE,
  tipo text NOT NULL, detalhe text NOT NULL, lido boolean NOT NULL DEFAULT false,
  criado_em timestamptz NOT NULL DEFAULT now(), UNIQUE (monitoramento_id, tipo, detalhe)
);

INSERT INTO schema_versao (versao) VALUES (1) ON CONFLICT DO NOTHING;
