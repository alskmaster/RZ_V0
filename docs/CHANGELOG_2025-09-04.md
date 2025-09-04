# Notas de Atualização — 2025-09-04

Este release foca em três frentes: (1) novos módulos (Capacidade, ITIL e Sumário Executivo), (2) engrenagens de customização padronizadas com "Nome Customizado" para todos os novos módulos, e (3) melhorias de UX/legibilidade e auto-descoberta para reduzir fricção com o usuário final.

## Novos Módulos

- Previsão de Capacidade (`capacity_forecast`)
  - Coleta `history.get` por `itemids`, calcula regressão linear (inclinação/Intercepto) e estima ETA para um limite.
  - Auto-descoberta: quando `itemids` não é informado, tenta chaves comuns (`vfs.fs.size[,pused]`, `vm.memory.size[pused]`, `system.cpu.util`).
  - Limite padrão: se a chave indicar percentual, assume 80% como limiar (configurável).
  - Classificação de risco: Crítico (<N dias), Atenção (N–M dias) e Estável, com ordenação por risco e maior inclinação.
  - Template mostra gráfico, legenda do limite, contagem por risco e tabela amigável (Host + Item, Risco, Tendência, Inclinação/dia, Intercepto e ETA).

- Disponibilidade por Incidente (ITIL) (`itil_availability`)
  - Sobrepõe incidentes (`problem.get`) na série do item (`history.get`), sombreando faixas no gráfico.
  - Auto-descoberta de `itemid` (ex.: `icmppingsec`) se não for informado.
  - Resumo por severidade e mensagens guiadas quando não há incidentes.

- Sumário Executivo (`executive_summary`)
  - KPIs de alto nível: total de hosts, SLA médio (se disponível via cache), total de incidentes e top ofensores por host.

## Engrenagens de Customização ("*_gear.js")

- Todos os novos módulos possuem engrenagem com "Nome Customizado".
- `capacity_forecast_gear.js`: itemids (CSV), value_type, limite, projeção, ocultar se vazio, limiares de risco e busca de itens (autocomplete por key).
- `critical_performance_gear.js`: itemids (CSV), value_type, sub-período, mínimo de pontos por série, ocultar se vazio e busca de itens.
- `itil_availability_gear.js`: itemid, value_type, severidades e ocultar se vazio.
- Também criados `mttr_gear.js` e `agent_status_gear.js` (Nome Customizado + filtros específicos).

## Melhorias de UX e Mensagens

- Troca de IDs frios por nomes amigáveis (Host + Nome do item) nas tabelas.
- Indicadores visuais de tendência (↑/↓/–) e classificação de risco na Capacidade.
- Resumos no topo (contagens) e dicas de ação quando não há dados.
- Opção "Ocultar se vazio" para evitar módulos sem valor no PDF.

## Auto-descoberta e Rotas de Apoio

- Crítico/Capacidade/ITIL fazem auto-descoberta quando IDs não são informados, reduzindo esforço do usuário.
- Rota auxiliar `GET /search_items/<client_id>?q=...` para autocomplete de itens por key (retorna `itemid`, `host`, `name`, `key_`).

## Arquivos Principais Alterados/Adicionados

- Colectors: `app/collectors/{capacity_forecast_collector.py,itil_availability_collector.py,executive_summary_collector.py}`; melhorias em `critical_performance_collector.py` e `agent_status_collector.py`.
- Templates: `app/templates/modules/{capacity_forecast.html,itil_availability.html,executive_summary.html,critical_performance.html}` (melhorias de UX e conteúdo).
- Gears: `app/static/js/modules/{capacity_forecast_gear.js,critical_performance_gear.js,itil_availability_gear.js,executive_summary_gear.js,mttr_gear.js,agent_status_gear.js}`.
- Form: inclusão dos scripts e nova URL em `app/templates/gerar_form.html`.
- Backend: `app/services.py` (registry dos novos módulos); rota `search_items` em `app/main/routes.py`.

## Como Usar

1. Na tela de gerar, adicione os módulos ao layout.
2. Abra a engrenagem de cada módulo para ajustar Nome Customizado e filtros.
3. Se preferir não informar IDs, os módulos tentam auto-descobrir itens comuns do cliente.
4. Opcional: marque "Ocultar se vazio" para suprimir módulos sem informação útil naquele período.

## Observações

- ETAs irreais são filtradas (ex.: muito distantes) e não aparecem.
- Se persistirem mensagens de "sem dados", ajuste o período ou selecione itens específicos via busca.

