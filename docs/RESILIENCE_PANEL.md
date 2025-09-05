Módulo: Painel de Resiliência (SLA Preciso)

Objetivo
- Exibir a disponibilidade (SLA) desconsiderando períodos de manutenção.

Versão atual (host-based)
- Cálculo host-based usando eventos de PING (correlação de problemas) para apurar SLA por host.
- Usa a meta de SLA do cliente (se definida) para realce abaixo da meta.

Opções de Customização (custom_options)
- host_name_contains: filtra hosts por substring do nome visível.
- exclude_hosts_contains: lista separada por vírgulas para excluir hosts por substring.
- period_sub_filter: 'full_month' | 'last_24h' | 'last_7d' (default: 'full_month').
- decimals: casas decimais para exibir em SLA (%).
- highlight_below_goal: bool, destaca linhas abaixo da meta do cliente.
- sort_by: 'sla' | 'downtime' | 'host'.
- sort_asc: bool, ordenação ascendente (default true).
- top_n: inteiro opcional para limitar a N linhas após ordenação.
- show_chart: bool, renderiza gráfico horizontal por host com linha de meta.
- chart_color: cor das barras.
- below_color: cor quando abaixo da meta.
- x_axis_0_100: bool, fixa eixo X de 0 a 100.

Saída
- Tabela: Host, SLA (%), Downtime (HH:MM:SS) com destaque abaixo da meta.
- Gráfico opcional de barras horizontais por host (base64) com linha de meta.

Roadmap (service-based)
- Migrar/alternar para APIs por serviço do Zabbix: `service.get` + `service.getsla` (com `maintenance: false`).
- Suportar filtros por serviços: `serviceids`, `service_name_contains`, `tags`.
- Adicionar opção de tendência temporal diária/semanal por serviço (`trend_granularity`: 'D'|'W') e `show_trend`.

