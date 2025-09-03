# Incidentes – Tabela e Gráficos

Este documento descreve o novo desenho do módulo de Incidentes, agora dividido em dois módulos independentes, cada um com engrenagem (customização) e template dedicados.

## Incidentes (Tabela)
- Identificador no layout: `incidents_table`
- Foco em apresentação tabular, com possibilidade de agrupar por Host ou por Problema.
- Filtros e opções suportadas:
  - `severities`: [info, warning, average, high, disaster]
  - `period_sub_filter`: full_month | last_24h | last_7d
  - `num_hosts`: Top N de hosts (opcional)
  - `host_name_contains`: filtro “contém” aplicado ao nome do host
  - `primary_grouping`: host | problem
  - `show_duration`: exibir coluna de duração
  - `show_acknowledgements`: exibir acknowledgements
- Coletor: `app/collectors/incidents_table_collector.py`
- Template: `app/templates/modules/incidents_table.html`

## Incidentes (Gráficos)
- Identificador no layout: `incidents_chart`
- Foco em visualizações:
  - Pizza por severidade
  - Barras por severidade
  - Top tipos de problema (barras)
  - Volume diário (série única)
  - Volume diário por severidade (barras empilhadas coloridas)
- Filtros e opções suportadas (custom_options):
  - `severities`: [info, warning, average, high, disaster]
  - `period_sub_filter`: full_month | last_24h | last_7d
  - `chart_type`: severity_pie | severity_bar | problem_type_bar | daily_volume | daily_volume_severity
  - `problem_type_top_n`: inteiro
  - `daily_volume_chart_type`: bar | line
  - `daily_volume_severities`: severidades (para o gráfico por severidade)
  - `x_axis_rotate_labels`: bool
  - `x_axis_alternate_days`: bool
- Coletor: `app/collectors/incidents_chart_collector.py`
- Template: `app/templates/modules/incidents_chart.html`

### Paleta de cores por severidade
- Não Classificado: `#9e9e9e`
- Informação: `#2196f3`
- Atenção: `#ffb300`
- Média: `#fb8c00`
- Alta: `#e53935`
- Desastre: `#8e0000`

## Observações
- O módulo legado `incidents` permanece compatível e agora renderiza apenas tabelas (mesmo template do `incidents_table`).
- É possível usar os dois módulos (tabela e gráficos) no mesmo relatório.

