Disponibilidade (SLA) — Como é Calculado

Visão Geral
- O SLA por host é calculado a partir dos eventos de Ping (Zabbix `icmpping`). Somamos o tempo em que o host esteve em estado de problema durante o período do relatório e aplicamos a fórmula clássica de disponibilidade.

Fonte de Dados
- Eventos: Zabbix `event.get` com `select_acknowledges=extend` no intervalo completo do relatório.
- Foco: somente problemas ligados a triggers de Ping (itens `icmpping`). Outros problemas (CPU, disco etc.) não entram no cálculo de disponibilidade.

Passo a Passo
1) Seleção de hosts válidos
   - Busca itens `icmpping` e seus triggers. Mantém apenas hosts que possuem esse Ping configurado.

2) Coleta de eventos no período
   - Coleta todos os eventos dos triggers de Ping no período.
   - Filtra “problemas” em nível de trigger: `source=0`, `object=0`, `value=1` (PROBLEM).

3) Correlação PROBLEM → OK
   - Para cada evento PROBLEM, encontra o primeiro evento OK (value=0) subsequente do mesmo trigger.
   - Se não existir OK no período, usa o fim do período como fechamento do intervalo.
   - Intervalos que atravessam o período são recortados nos limites do mês.

4) Soma de downtime por host
   - Converte cada intervalo PROBLEM→OK em segundos e soma por host.

5) Fórmula do SLA
   - `total = fim_período − início_período` (em segundos)
   - `SLA_host = 100 * (1 − downtime_host / total)`
   - O valor é limitado a [0, 100]. Também é exposto o “Tempo Indisponível” em HH:MM:SS.

Saída e Consumo
- DataFrame `df_sla_problems` com as colunas: `Host`, `SLA (%)`, `Tempo Indisponível`, `Downtime (s)`.
- Módulos que usam esta saída:
  - SLA — Tabela: ordenação, Top N, Meta/Highlight, filtro “Filtrar hosts (contém)”, comparação com mês anterior.
  - SLA — Gráfico: aplicação de “Ordem” (Asc/Desc) diretamente sobre a coluna de SLA, Top N, destaque abaixo da meta.

Limites e Observações
- O SLA reflete apenas indisponibilidades detectadas pelos triggers de Ping. Se não houver PROBLEM quando o host está “fora”, esse período não contará como downtime.
- Vários eventos do mesmo trigger são ordenados por tempo; cada PROBLEM fecha com o primeiro OK seguinte.
- Incidentes não relacionados a Ping (CPU/mem/disk etc.) não afetam o SLA.

Referências no Código
- Correlação e cálculo: `app/services.py` — métodos `_correlate_problems` e `_calculate_sla`.
- Pré-coleta e cache de disponibilidade: `ReportGenerator._collect_availability_data`.
