"""Alarmes, avisos por e-mail e painel (sub-etapa 2.6).

Tudo que importa avisa por e-mail (tópico SNS `sonar-automais-alertas`; cada e-mail precisa clicar em
"Confirm subscription" uma vez):

  API          erros não tratados (log ERRO_NAO_TRATADO), erros/limitação das Lambdas, lentidão (p95), 5xx no gateway
  Coleta       tarefa do Fargate que terminou com erro (evento do ECS), pedido sob demanda que não iniciou
               (log COLETA_FALHOU), e "nenhuma coleta em 24 h"
  Banco        CPU alta, pouco espaço, pouca memória, muitas conexões

Painel `sonar-automais` no CloudWatch: buscas (visitante x conta), cadastros (Cognito e CNPJs salvos), erros,
tempo de resposta, coletas e banco. As buscas vêm da linha JSON que a API grava por requisição (METRICAS_LOG=1).

Custo: 10 alarmes e 10 métricas próprias grátis por mês; acima disso ~US$ 0,10 por alarme e US$ 0,30 por métrica.
"""
from aws_cdk import Duration, Stack
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_acoes
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as alvos
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as assinaturas
from constructs import Construct

from .api import Api
from .banco import Banco
from .tarefas import Tarefas

NS = "SonarLicitamais"
CINCO_MIN = Duration.minutes(5)


class Monitoramento(Stack):
    def __init__(self, escopo: Construct, id_: str, *, api: Api, banco: Banco, tarefas: Tarefas,
                 emails: list[str], **kw) -> None:
        super().__init__(escopo, id_, **kw)
        self.topico = sns.Topic(self, "Alertas", topic_name="sonar-automais-alertas",
                                display_name="Sonar Auto+ alertas")
        for e in emails:
            self.topico.add_subscription(assinaturas.EmailSubscription(e))
        acao = cw_acoes.SnsAction(self.topico)
        self.alarmes: list[cw.Alarm] = []

        def alarme(nome: str, metrica: cw.IMetric, limite: float, descricao: str, *, maior: bool = True,
                   periodos: int = 1, sem_dados=cw.TreatMissingData.NOT_BREACHING) -> cw.Alarm:
            a = cw.Alarm(self, nome.replace(" ", ""), alarm_name=f"sonar-automais {nome}", metric=metrica,
                         threshold=limite, evaluation_periods=periodos, datapoints_to_alarm=periodos,
                         alarm_description=descricao, treat_missing_data=sem_dados,
                         comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD if maior
                         else cw.ComparisonOperator.LESS_THAN_THRESHOLD)
            a.add_alarm_action(acao)
            a.add_ok_action(acao)  # avisa também quando normaliza
            self.alarmes.append(a)
            return a

        def filtro(nome: str, grupo: logs.ILogGroup, padrao: logs.IFilterPattern, metrica: str) -> cw.Metric:
            logs.MetricFilter(self, nome, log_group=grupo, filter_pattern=padrao, metric_namespace=NS,
                              metric_name=metrica, metric_value="1")
            return cw.Metric(namespace=NS, metric_name=metrica, statistic="Sum", period=CINCO_MIN)

        # ------------------------------------------------------------ API
        erros_app = filtro("FiltroErroApi", api.logs_api, logs.FilterPattern.literal('"ERRO_NAO_TRATADO"'), "ErrosApi")
        erros_borda = filtro("FiltroErroBorda", api.logs_borda, logs.FilterPattern.literal('"ERRO_NAO_TRATADO"'),
                             "ErrosBorda")
        alarme("API erro nao tratado", erros_app, 1,
               "A API respondeu 'Tivemos um problema no servidor'. Veja /sonar-automais/api (procure ERRO_NAO_TRATADO).")
        alarme("Borda erro", erros_borda, 1,
               "A Lambda da API falhou (timeout ou exceção) e a borda devolveu 502. Veja /sonar-automais/borda.")
        erros_lambda = cw.MathExpression(
            expression="api + borda", period=CINCO_MIN, label="Erros das Lambdas",
            using_metrics={"api": api.funcao_api.metric_errors(period=CINCO_MIN),
                           "borda": api.borda.metric_errors(period=CINCO_MIN)})
        alarme("Lambdas com erro", erros_lambda, 3, "3+ execuções das Lambdas falharam em 5 min.")
        limitadas = cw.MathExpression(
            expression="api + borda", period=CINCO_MIN, label="Execuções limitadas",
            using_metrics={"api": api.funcao_api.metric_throttles(period=CINCO_MIN),
                           "borda": api.borda.metric_throttles(period=CINCO_MIN)})
        alarme("Lambdas limitadas", limitadas, 1, "A AWS recusou execuções por limite de concorrência.")
        lenta = api.borda.metric_duration(statistic="p95", period=CINCO_MIN)
        alarme("API lenta", lenta, 10000, "95% das respostas acima de 10 s por 15 min.", periodos=3)
        gw_5xx = cw.Metric(namespace="AWS/ApiGateway", metric_name="5xx", statistic="Sum", period=CINCO_MIN,
                           dimensions_map={"ApiId": api.http.api_id, "Stage": "$default"})
        alarme("Gateway 5xx", gw_5xx, 5, "5+ respostas 5xx em 5 min (banco fora, erro interno ou Receita fora).")

        # ------------------------------------------------------------ coleta (Fargate)
        regra = events.Rule(self, "TarefaFalhou", rule_name="sonar-automais-coleta-falhou",
                            description="Tarefa de coleta/migração terminou com erro",
                            event_pattern=events.EventPattern(
                                source=["aws.ecs"], detail_type=["ECS Task State Change"],
                                detail={"clusterArn": [tarefas.cluster.cluster_arn], "lastStatus": ["STOPPED"],
                                        "containers": {"exitCode": [{"anything-but": 0}]}}))
        regra.add_target(alvos.SnsTopic(self.topico, message=events.RuleTargetInput.from_text(
            f"Sonar Auto+: a coleta/migração no Fargate terminou com erro.\n"
            f"Motivo: {events.EventField.from_path('$.detail.stoppedReason')}\n"
            f"Comando: {events.EventField.from_path('$.detail.overrides.containerOverrides[0].command')}\n"
            f"Tarefa: {events.EventField.from_path('$.detail.taskArn')}\n"
            "Logs: aws logs tail /sonar-automais/tarefas --since 1h")))

        falhou = filtro("FiltroColetaFalhou", tarefas.logs, logs.FilterPattern.literal('"COLETA_FALHOU"'),
                        "ColetaFalhou")
        falhou_borda = filtro("FiltroColetaBorda", api.logs_borda, logs.FilterPattern.literal('"COLETA_FALHOU"'),
                              "ColetaNaoIniciou")
        alarme("Coleta UF falhou", falhou, 1, "Uma UF não foi coletada (PNCP fora?). Veja /sonar-automais/tarefas.")
        alarme("Coleta sob demanda nao iniciou", falhou_borda, 1,
               "A borda não conseguiu iniciar a tarefa de coleta da UF pedida. Veja /sonar-automais/borda.")
        filtro("FiltroColetaOk", tarefas.logs, logs.FilterPattern.literal('"editais novos/alterados"'), "ColetasUF")
        alarme("Sem coleta em 24h",
               cw.Metric(namespace=NS, metric_name="ColetasUF", statistic="Sum", period=Duration.hours(12)),
               1, "Nenhuma UF foi coletada nas últimas 24 h (agenda parada ou imagem quebrada).", maior=False,
               periodos=2, sem_dados=cw.TreatMissingData.BREACHING)

        # ------------------------------------------------------------ banco
        rds = banco.instancia
        alarme("Banco CPU alta", rds.metric_cpu_utilization(period=CINCO_MIN), 80, "CPU do RDS acima de 80% por 15 min.",
               periodos=3)
        alarme("Banco pouco espaco", rds.metric_free_storage_space(period=CINCO_MIN), 2 * 1024 ** 3,
               "Menos de 2 GB livres no RDS (20 GB sem crescimento automático no plano gratuito).", maior=False)
        alarme("Banco pouca memoria", rds.metric_freeable_memory(period=CINCO_MIN), 64 * 1024 ** 2,
               "Menos de 64 MB de memória livre no RDS por 15 min.", maior=False, periodos=3)
        alarme("Banco muitas conexoes", rds.metric_database_connections(period=CINCO_MIN), 60,
               "60+ conexões abertas no RDS (t4g.micro aguenta ~80).")

        # ------------------------------------------------------------ métricas de uso (painel)
        logs.MetricFilter(self, "FiltroBuscas", log_group=api.logs_api, metric_namespace=NS, metric_name="Buscas",
                          metric_value="1", dimensions={"Usuario": "$.usuario"},
                          filter_pattern=logs.FilterPattern.literal(
                              '{ $.metrica = "requisicao" && $.rota = "/busca/{cnpj}" && $.status = 200 }'))
        logs.MetricFilter(self, "FiltroLimite", log_group=api.logs_api, metric_namespace=NS,
                          metric_name="LimiteAtingido", metric_value="1", dimensions={"Usuario": "$.usuario"},
                          filter_pattern=logs.FilterPattern.literal(
                              '{ $.metrica = "requisicao" && $.rota = "/busca/{cnpj}" && $.status = 429 }'))
        logs.MetricFilter(self, "FiltroEmpresas", log_group=api.logs_api, metric_namespace=NS,
                          metric_name="CnpjsSalvos", metric_value="1",
                          filter_pattern=logs.FilterPattern.literal(
                              '{ $.metrica = "requisicao" && $.rota = "/empresas" && $.metodo = "POST" '
                              '&& $.status = 201 }'))
        hora = Duration.hours(1)

        def uso(metrica: str, quem: str | None = None, rotulo: str | None = None) -> cw.Metric:
            return cw.Metric(namespace=NS, metric_name=metrica, statistic="Sum", period=hora,
                             dimensions_map={"Usuario": quem} if quem else None, label=rotulo or metrica)

        cadastros = cw.Metric(namespace="AWS/Cognito", metric_name="SignUpSuccesses", statistic="Sum", period=hora,
                              dimensions_map={"UserPool": api.usuarios.user_pool_id,
                                              "UserPoolClient": api.cliente.user_pool_client_id},
                              label="Contas criadas")
        painel = cw.Dashboard(self, "Painel", dashboard_name="sonar-automais",
                              default_interval=Duration.days(7))
        painel.add_widgets(
            cw.TextWidget(markdown="# Sonar Auto+ — uso e saúde\nBuscas e cadastros por hora; alarmes à direita. "
                                   "Logs: /sonar-automais/api, /borda, /tarefas.", width=24, height=2))
        painel.add_widgets(
            cw.GraphWidget(title="Buscas por hora", width=8, left=[
                uso("Buscas", "visitante", "Visitante"), uso("Buscas", "conta", "Com conta"),
                uso("LimiteAtingido", "visitante", "Visitante no limite")]),
            cw.GraphWidget(title="Cadastros", width=8, left=[cadastros, uso("CnpjsSalvos", rotulo="CNPJs salvos")]),
            cw.AlarmStatusWidget(title="Alarmes", width=8, height=6, alarms=self.alarmes))
        painel.add_widgets(
            cw.GraphWidget(title="Erros", width=8, left=[gw_5xx, erros_app, erros_borda]),
            cw.GraphWidget(title="Tempo de resposta (ms)", width=8, left=[
                api.borda.metric_duration(statistic="p50", period=CINCO_MIN, label="p50"),
                api.borda.metric_duration(statistic="p95", period=CINCO_MIN, label="p95")]),
            cw.GraphWidget(title="Coletas", width=8, left=[
                cw.Metric(namespace=NS, metric_name="ColetasUF", statistic="Sum", period=hora, label="UFs coletadas"),
                cw.Metric(namespace=NS, metric_name="ColetaFalhou", statistic="Sum", period=hora, label="Falhas")]))
        painel.add_widgets(
            cw.GraphWidget(title="Banco: CPU (%) e conexões", width=12, left=[rds.metric_cpu_utilization()],
                           right=[rds.metric_database_connections()]),
            cw.GraphWidget(title="Banco: espaço e memória livres (bytes)", width=12,
                           left=[rds.metric_free_storage_space()], right=[rds.metric_freeable_memory()]))
