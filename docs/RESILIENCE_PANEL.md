Módulo: Painel de Resiliência (SLA Preciso)

Objetivo
- Exibir a disponibilidade (SLA) de serviços de TI do Zabbix desconsiderando períodos de manutenção.

API utilizada
- service.get: descoberta/seleção de serviços (por ids, nome, tags)
- service.getsla: cálculo de SLA por intervalo(s), com `maintenance: false`

Opções de Customização (custom_options)
- serviceids: lista de IDs de serviços (opcional)
- service_name_contains: filtro por substring no nome (opcional)
- tags: lista de objetos {tag, value} para filtrar serviços (opcional)
- target_sla: meta em %, usada para destacar serviços abaixo da meta. Fallback: SLA do cliente.
- show_trend: bool (default True) para exibir o gráfico de tendência
- trend_granularity: 'D' (dia) | 'W' (semana), default 'D'

Saída
- Gráfico de tendência (quando ativado): evolução diária/semanal do SLA por serviço.
- Tabela: Serviço, SLA (%) do período, Downtime (HH:MM:SS) e destaque de meta.

Notas de Integração
- O período é controlado pelo mês de referência do relatório.
- A seleção de grupos de hosts ocorre ao selecionar o cliente no formulário; serviços são globais no Zabbix e devem ser refinados via `serviceids`, nome ou `tags`.
- Este módulo não depende dos itens de Ping, pois delega o cálculo ao Zabbix.

