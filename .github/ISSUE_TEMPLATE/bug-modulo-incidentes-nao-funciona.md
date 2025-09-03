---
name: Bug – Módulo Incidentes não atualiza/funciona
about: Relatar falha nas atualizações do módulo de Incidentes
title: "[Incidentes] Atualizações não funcionam / falha na renderização"
labels: bug, module:incidents, priority:high
assignees: ''
---

Contexto
- Após as últimas alterações no módulo de Incidentes, as atualizações não estão funcionando como esperado. O módulo não reflete as novas customizações e/ou falha ao renderizar a seção no relatório.
- Histórico relevante (commits locais ainda não publicados):
  - 9927fde – feat: Aprimora módulo de Incidentes com customizações e gráfico de severidade
  - b669c96 – feat: Implementa agrupamento avançado e filtro por nome de host no módulo de Incidentes
  - 56ea934 – feat: Integra módulo de Incidentes ao sistema
  - 17b0922 – fix: Restaura módulo de Incidentes para estado funcional verificado
- Observação: há alterações locais não commitadas em `app/collectors/incidents_collector.py`, `app/static/js/modules/incidents_gear.js` e `app/templates/modules/incidents.html`.

Ambiente
- App Flask; geração de relatórios via `ReportGenerator` (thread).
- Zabbix configurado via .env.
- Dependências conforme `requirements.txt` (sem pinagem de versão).

Passos para Reproduzir
1) Na tela “Gerar”, adicionar o módulo “Incidentes” ao layout.
2) Configurar customizações (ex.: severities, primary_grouping=host, filtros de período e host_name_contains).
3) Selecionar cliente e mês de referência e iniciar a geração.
4) Acompanhar o status e abrir o PDF gerado.

Resultado Atual
- A seção “Incidentes” não é exibida, ou aparece vazia, ou apresenta erros visuais.
- Em alguns casos, a coleta pode retornar None e o HTML do módulo não é renderizado.

Resultado Esperado
- A seção deve exibir:
  - Resumo (contagem total e distribuição por severidade),
  - Lista agrupada (por host ou por problema) com horário, duração e acknowledgements (quando habilitado),
  - Gráfico(s) (ex.: pizza por severidade, volume diário) quando configurado.

Evidências/Logs
- Verificar `server.err.log` e `server.out.log` na raiz do projeto durante a geração.
- Coleta de eventos: `ReportGenerator.obter_eventos_wrapper` e `ReportGenerator.obter_eventos`.
- Coletor: `app/collectors/incidents_collector.py` (possíveis problemas identificados):
  - Duplicação de blocos de código e returns dentro de `collect()` que podem interromper o fluxo (existe código repetido após um `return`).
  - `print()` de debug no coletor; ideal mover para `current_app.logger`.
  - Conversões de tipos para filtrar severidades (string vs int) podem falhar dependendo do payload do Zabbix.

Impacto
- Geração de relatórios com módulo “Incidentes” fica inconsistente ou quebrada, afetando entregas mensais.

Hipóteses de Causa Raiz
- Artefatos de merge/duplicação em `incidents_collector.py` (fluxo interrompido por `return` antecipado e código repetido).
- Divergências no schema de eventos retornado pela API do Zabbix (tipos de campos `source/object/value/severity`).
- Alterações locais não commitadas conflitando com o estado dos templates/front (gear JS & template Jinja).

Plano de Correção Proposto
1) Limpar `app/collectors/incidents_collector.py`:
   - Remover blocos duplicados e `print()`; padronizar logs.
   - Garantir que `collect()` tenha fluxo único até o `return` final.
   - Normalizar tipos (`severity`, `value`, `source`, `object`) antes de filtros.
2) Validar integração front/back:
   - Conferir `app/static/js/modules/incidents_gear.js` e `app/templates/modules/incidents.html` com as chaves esperadas no `data` do coletor.
3) Adicionar teste manual de diagnóstico:
   - Geração somente do módulo Incidentes em diferentes janelas (mês cheio, last_7d, last_24h) com/sem filtros.
4) Opcional: criar rota de debug focada em Incidentes (similar ao `/admin/debug_collect`).

Checklist
- [ ] Reproduzir o erro com logs ligados em DEBUG.
- [ ] Corrigir duplicações e fluxo em `incidents_collector.py`.
- [ ] Validar filtros de severidade e período com diferentes clientes.
- [ ] Ajustar template/JS se houver chaves divergentes.
- [ ] Documentar no README (seção do módulo Incidentes) as opções suportadas.

Notas Adicionais
- Ignorar `instance/*.db` no `.gitignore` para evitar versionar o banco local.
- Após correção, considerar adicionar testes básicos de integração (mock Zabbix) para o coletor.

