# RZ_V0 — Evoluções e Guia Rápido

Este documento resume as principais evoluções realizadas e como utilizá-las no dia a dia. O foco foi tornar a coleta e a montagem de relatórios muito mais resiliente, com cadastro dinâmico de métricas e diagnóstico simples no Admin.

## Visão Geral das Evoluções
- Coleta resiliente (CPU, Memória, Disco):
  - Perfis do banco + descoberta automática de chaves por host.
  - Primeiro tenta `trend.get`; se vazio, faz fallback para `history.get` com agregação min/avg/max.
  - Seleção por host do “melhor” perfil (menor prioridade numérica), evitando misturar DIRECT/INVERSE.
- Wi‑Fi unificado:
  - Mesmo padrão de robustez, mantendo gráficos e tabelas existentes do módulo.
  - Fallback para `history.get` (value_type=3) quando trends não estão disponíveis.
- Descoberta de métricas no Admin:
  - Card “Descobrir no Zabbix” com seleção de cliente + tipo (inclui “Wi‑Fi (Clientes)”).
  - Cadastro em lote (“Salvar Selecionados”) com prioridade/ativo/descrição.
- Perfis de Métricas:
  - CRUD em Admin > Perfis de Coleta de Métricas (CPU, Memória, Disco e Wi‑Fi).
  - Cada perfil define key, prioridade e tipo de cálculo (DIRECT/INVERSE).
- Diagnóstico rápido:
  - Endpoint `/admin/debug_collect?client_id=<id>&module=cpu|mem|disk|wifi&mes_ref=YYYY-MM`.
  - Retorna hosts, itens encontrados, exemplos de key_ e pontos de dados (trends/history).
- Correções e utilidades:
  - `get_items` ajustado para usar `search {'key_': '<string>'}` (antes passava lista e retornava 0 itens).
  - Agregador robusto com chunking para `trend.get/history.get`.
  - CLI `flask reset-superadmin --password "..."` para criar/atualizar o superadmin.

## Onde Foi Implementado
- Engine de coleta: `app/collectors/robust_metric_engine.py`
- Coletores:
  - CPU: `app/collectors/cpu_collector.py`
  - Memória: `app/collectors/mem_collector.py`
  - Disco: `app/collectors/disk_collector.py`
  - Wi‑Fi: `app/collectors/wifi_collector.py`
- Zabbix/Serviços:
  - Agregação robusta + history/trends: `app/services.py`
  - Ajuste de `get_items`: `app/services.py`
  - Chamadas Zabbix: `app/zabbix_api.py`
- Admin:
  - Perfis + Descoberta: `app/admin/routes.py`, `app/admin/metric_keys_api.py`
  - Diagnóstico: `app/admin/debug_routes.py`
  - UI: `app/templates/admin/metric_keys.html`

## Como Usar (Resumo)
1) Cadastre perfis em Admin > Perfis de Coleta de Métricas.
   - Tipos: cpu, memory, disk, wifi_clients.
   - Use “Descobrir no Zabbix” para sugerir chaves existentes.
2) Gere o relatório (tela “Gerar”).
   - Selecione cliente, mês (YYYY-MM) e módulos (CPU/MEM/DISK/Wi‑Fi, etc.).
3) Se algum módulo vier vazio, rode o diagnóstico:
   - `/admin/debug_collect?client_id=<id>&module=cpu|mem|disk|wifi&mes_ref=YYYY-MM`
   - Ajuste perfis se necessário (prioridade e DIRECT/INVERSE).

## Notas por Módulo
- CPU: prefere `system.cpu.util[,idle]` (INVERSE); alternativas como `system.cpu.util[,user]`/`system.cpu.util`.
- Memória: `vm.memory.size[pused]` (DIRECT) ou `vm.memory.size[pavailable|pfree]` (INVERSE).
- Disco: `vfs.fs.size[/fs,pused]` (DIRECT) ou `...,[pfree|pavailable]` (INVERSE). A engine escolhe por host a melhor opção.
- Wi‑Fi: chaves comuns como `clientcountnumber`, `wlan.bss.numsta`, `StationsConnected`, `wlan.client.count`.

### Opções (Engrenagem) — SLA
- sla_chart (gráfico):
  - `top_n`, `order`, `color`, `target_sla`, `below_color`, `x_axis_0_100`.
- sla_table (tabela):
  - `target_sla`, `show_goal`, `show_ip`, `compare_to_previous_month`, `show_previous_sla`, `show_improvement`, `sort_by`, `sort_asc`, `top_n`, `hide_summary`, `show_downtime`.

## Boas Práticas
- Dê prioridade baixa (ex.: 1) para a key preferencial e mantenha alternativas com prioridades maiores.
- Evite perfis DIRECT e INVERSE ativos ao mesmo tempo para o mesmo contexto — a engine já seleciona por host, mas clareza ajuda.
- Para Disco, utilize filtros (tmpfs/overlay/loop/snap) conforme evolução da engine.

## Próximos Passos Sugeridos
- “Perfil vencedor por host”: cachear a key escolhida por host/tipo para acelerar coletas futuras.
- Multi‑Zabbix por cliente: usar `Client.zabbix_url/user/password` diretamente na engine/coleta.
- UI de pré‑checagem: mostrar hosts/itens/dados antes de gerar o relatório.
- Paralelização com limites (throttling) para grandes volumes de itens.

## Melhorias de UX (acentuação e mensagens)
- Mensagens na tela de geração/polling normalizadas e com acentuação correta.
- Backend sanitiza mensagens de progresso para ASCII quando necessário.

## Utilidades
- Resetar/criar superadmin:
  - `FLASK_APP=run.py flask reset-superadmin --password "NovaSenhaForte"`
- Diagnóstico por módulo/mês:
  - `GET /admin/debug_collect?client_id=<id>&module=cpu|mem|disk|wifi&mes_ref=YYYY-MM`

—
Em caso de dúvidas ou sugestões de evolução, abra uma issue interna.

