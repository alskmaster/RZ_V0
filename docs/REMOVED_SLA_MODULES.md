# Remoção de Módulos de SLA e Disponibilidade (Hard-remove)

Este documento detalha a remoção completa dos módulos de SLA/Disponibilidade e correlatos.

## Motivação
- Alinhar o cálculo de disponibilidade ao processo desejado, reduzindo ambiguidade entre métricas de Ping e incidentes.
- Simplificar a base enquanto um novo desenho de disponibilidade é validado.

## Escopo Removido
- Tipos de módulo removidos do sistema e do builder:
  - sla, sla_table, sla_chart, sla_plus
  - kpi, 	op_hosts, 	op_problems, stress
  - sla_incidents_table

## Arquivos Removidos
- Coletores:
  - pp/collectors/sla_collector.py
  - pp/collectors/sla_table_collector.py
  - pp/collectors/sla_chart_collector.py
  - pp/collectors/sla_plus_collector.py
  - pp/collectors/kpi_collector.py
  - pp/collectors/top_hosts_collector.py
  - pp/collectors/top_problems_collector.py
  - pp/collectors/stress_collector.py
  - pp/collectors/sla_incidents_table_collector.py
- Templates:
  - pp/templates/modules/sla.html
  - pp/templates/modules/sla_table.html
  - pp/templates/modules/sla_chart.html
  - pp/templates/modules/sla_plus.html
  - pp/templates/modules/_cards_sla_plus.html
  - pp/templates/modules/kpi.html
  - pp/templates/modules/top_hosts.html
  - pp/templates/modules/top_problems.html
  - pp/templates/modules/stress.html
  - pp/templates/modules/sla_incidents_table.html
- Engrenagens (JS):
  - pp/static/js/modules/sla_chart_gear.js
  - pp/static/js/modules/sla_table_gear.js
  - pp/static/js/modules/sla_plus_gear.js
  - pp/static/js/modules/sla_incidents_table_gear.js

## Alterações de Código
- pp/services.py
  - Removidas importações e entradas no COLLECTOR_MAP para todos os módulos acima.
  - Desativada a pré-coleta de disponibilidade (vailability_module_types = set()).
- pp/main/routes.py
  - Removidas adições dos módulos na rota get_available_modules.
  - Atualizada a limpeza de legados no builder para descartar sla, sla_*, kpi, 	op_hosts, 	op_problems, stress.
- pp/templates/gerar_form.html
  - Removidas referências <script> dos JS de engrenagem de SLA.

## Impacto e Compatibilidade
- Layouts antigos contendo os tipos removidos serão limpos no builder (não aparecem mais nem são executados).
- Módulos preservados: Incidentes (Tabela/Gráfico), CPU, Memória, Disco, Latência, Perda, Inventário, HTML, Tráfego.
- O núcleo de disponibilidade em services.py permanece, mas não é mais utilizado até um novo design ser validado.

## Próximos Passos
- Validar relatórios sem os módulos removidos.
- Evoluir o novo desenho de disponibilidade com base em incidentes/SLM acordado (quando for reintroduzido).
