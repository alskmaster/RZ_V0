# Remo��o de M�dulos de SLA e Disponibilidade (Hard-remove)

Este documento detalha a remo��o completa dos m�dulos de SLA/Disponibilidade e correlatos.

## Motiva��o
- Alinhar o c�lculo de disponibilidade ao processo desejado, reduzindo ambiguidade entre m�tricas de Ping e incidentes.
- Simplificar a base enquanto um novo desenho de disponibilidade � validado.

## Escopo Removido
- Tipos de m�dulo removidos do sistema e do builder:
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

## Altera��es de C�digo
- pp/services.py
  - Removidas importa��es e entradas no COLLECTOR_MAP para todos os m�dulos acima.
  - Desativada a pr�-coleta de disponibilidade (vailability_module_types = set()).
- pp/main/routes.py
  - Removidas adi��es dos m�dulos na rota get_available_modules.
  - Atualizada a limpeza de legados no builder para descartar sla, sla_*, kpi, 	op_hosts, 	op_problems, stress.
- pp/templates/gerar_form.html
  - Removidas refer�ncias <script> dos JS de engrenagem de SLA.

## Impacto e Compatibilidade
- Layouts antigos contendo os tipos removidos ser�o limpos no builder (n�o aparecem mais nem s�o executados).
- M�dulos preservados: Incidentes (Tabela/Gr�fico), CPU, Mem�ria, Disco, Lat�ncia, Perda, Invent�rio, HTML, Tr�fego.
- O n�cleo de disponibilidade em services.py permanece, mas n�o � mais utilizado at� um novo design ser validado.

## Pr�ximos Passos
- Validar relat�rios sem os m�dulos removidos.
- Evoluir o novo desenho de disponibilidade com base em incidentes/SLM acordado (quando for reintroduzido).
