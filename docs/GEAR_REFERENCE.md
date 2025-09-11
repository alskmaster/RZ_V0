Guia de Referência para GEAR (Personalização de Módulos)

Objetivo
- Padronizar a criação de engrenagens (modais de personalização) dos módulos.
- Facilitar reuso e manutenção, tomando o GEAR de Incidentes (Tabela) como referência.

Contrato esperado pelo builder (gerar_form.js)
- Registrar um customizer em `window.ModuleCustomizers['<module_type>']` com a seguinte interface:
  - `_ensure()`: cria/anexa o modal no DOM (se ainda não existir) e popula `this.modal` (bootstrap.Modal) e `this.elements` (refs dos inputs).
  - `load(options)`: recebe `module.custom_options` atual, preenche os campos, e (opcional) carrega o título do módulo a partir de `window.currentModuleToCustomize.title`.
  - `save()`: retorna um objeto com as opções salvas. Para título do módulo, retornar `__title` (string) que o builder usa para atualizar `module.title`.

Boas práticas (baseadas no Incidentes - Tabela)
- Modal:
  - Sempre anexar com `document.body.appendChild(tpl.firstElementChild)` após montar `tpl.innerHTML`.
  - Manter rótulos e placeholders claros, com acentuação correta.
  - Agrupar campos em colunas responsivas (ex.: `col-md-6`).

- Campos comuns recomendados:
  - Título do módulo (texto) → `__title`.
  - Severidades (checkboxes) quando fizer sentido (ex.: módulos de incidentes).
  - Período (select) com: Mês Completo, Últimos 7 dias, Últimas 24h.
  - Filtros de host/problema (contendo) e exclusões (lista separada por vírgula).
  - Filtros de tags incluir/excluir (texto).
  - Agrupamento (select) e Top N (numérico), quando aplicável.
  - Opções booleanas (checkboxes) para mostrar/ocultar seções.
  - Filtro de ACK (select) quando aplicável (Todos / Somente com ACK / Somente sem ACK).

- Nomeação e persistência:
  - `elements`: guarde todas as referências dos inputs.
  - `load()`: proteja acessos (`el.campo && ...`) para compatibilidade.
  - `save()`: converta tipos apropriadamente (ex.: parseInt em numéricos, booleans com `!!`).
  - Retorne `null` para valores vazios em filtros textuais quando não preencher, evitando poluir o layout.

Exemplo de referência
- Consulte `app/static/js/modules/incidents_table_gear.js` como implementação completa, incluindo:
  - Campo de título (`__title`).
  - Campos/filtros listados acima.
  - Anexo do modal ao DOM.

Template básico
- Um template pronto para copiar/colar está em `app/static/js/modules/gear_reference_template.js`.

