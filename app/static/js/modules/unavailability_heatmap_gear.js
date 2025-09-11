(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['unavailability_heatmap'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureUhmModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('uhmTitle'),
        periodSubFilter: document.getElementById('uhmPeriodSubFilter'),
        // Opções gerais
        showSummary: document.getElementById('uhmShowSummary'),
        // Severidades
        sevInfo: document.getElementById('uhmSevInfo'),
        sevWarn: document.getElementById('uhmSevWarn'),
        sevAvg: document.getElementById('uhmSevAvg'),
        sevHigh: document.getElementById('uhmSevHigh'),
        sevDis: document.getElementById('uhmSevDis'),
        // Filtros
        hostContains: document.getElementById('uhmHostContains'),
        excludeHosts: document.getElementById('uhmExcludeHosts'),
        triggerContains: document.getElementById('uhmTriggerContains'),
        excludeTriggers: document.getElementById('uhmExcludeTriggers'),
        tagsInclude: document.getElementById('uhmTagsInclude'),
        tagsExclude: document.getElementById('uhmTagsExclude'),
        ackFilter: document.getElementById('uhmAckFilter'),
        // Paleta / anotação
        palette: document.getElementById('uhmPalette'),
        annotate: document.getElementById('uhmAnnotate'),
        // Ação
        saveBtn: document.getElementById('saveUhmBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      if (el.showSummary) el.showSummary.checked = (o.show_summary !== false);
      // filtros
      el.hostContains.value = o.host_name_contains || '';
      if (el.excludeHosts) el.excludeHosts.value = o.exclude_hosts_contains || '';
      if (el.triggerContains) el.triggerContains.value = o.trigger_name_contains || '';
      if (el.excludeTriggers) el.excludeTriggers.value = o.exclude_triggers_contains || '';
      if (el.tagsInclude) el.tagsInclude.value = o.tags_include || '';
      if (el.tagsExclude) el.tagsExclude.value = o.tags_exclude || '';
      if (el.ackFilter) el.ackFilter.value = (o.ack_filter || 'all');
      // paleta/anotação
      el.palette.value = o.palette || 'OrRd';
      el.annotate.checked = (o.annotate !== false);
      // severidades
      const sel = new Set(o.severities || ['info','warning','average','high','disaster']);
      el.sevInfo.checked = sel.has('info');
      el.sevWarn.checked = sel.has('warning');
      el.sevAvg.checked = sel.has('average');
      el.sevHigh.checked = sel.has('high');
      el.sevDis.checked = sel.has('disaster');
      // salvar
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      const severities = [];
      if (el.sevInfo.checked) severities.push('info');
      if (el.sevWarn.checked) severities.push('warning');
      if (el.sevAvg.checked) severities.push('average');
      if (el.sevHigh.checked) severities.push('high');
      if (el.sevDis.checked) severities.push('disaster');
      return {
        __title: el.title.value || '',
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        show_summary: el.showSummary ? !!el.showSummary.checked : true,
        // severidades
        severities: severities.length ? severities : ['info','warning','average','high','disaster'],
        // filtros
        host_name_contains: el.hostContains.value || null,
        exclude_hosts_contains: el.excludeHosts ? (el.excludeHosts.value || null) : null,
        trigger_name_contains: el.triggerContains ? (el.triggerContains.value || null) : null,
        exclude_triggers_contains: el.excludeTriggers ? (el.excludeTriggers.value || null) : null,
        tags_include: el.tagsInclude ? (el.tagsInclude.value || null) : null,
        tags_exclude: el.tagsExclude ? (el.tagsExclude.value || null) : null,
        ack_filter: el.ackFilter ? (el.ackFilter.value || 'all') : 'all',
        // visual
        palette: el.palette.value || 'OrRd',
        annotate: !!el.annotate.checked
      };
    }
  };

  function ensureUhmModal(){
    let el = document.getElementById('customizeUhmModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeUhmModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Personalizar Módulo: Mapa de Calor de Indisponibilidade</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <!-- Título do módulo -->
            <div class="col-12">
              <label class="form-label" for="uhmTitle">Título do módulo</label>
              <input type="text" class="form-control" id="uhmTitle" placeholder="Ex: Mapa de Calor de Indisponibilidade"/>
            </div>
            <!-- Filtro de Período -->
            <div class="col-md-4">
              <label class="form-label" for="uhmPeriodSubFilter">Período</label>
              <select class="form-select" id="uhmPeriodSubFilter">
                <option value="full_month">Mês Completo</option>
                <option value="last_7d">Últimos 7 dias</option>
                <option value="last_24h">Últimas 24h</option>
              </select>
            </div>
            <!-- Exibir Resumo Explicativo -->
            <div class="col-md-4 form-check d-flex align-items-end">
              <div>
                <input class="form-check-input" type="checkbox" id="uhmShowSummary" checked>
                <label class="form-check-label" for="uhmShowSummary">Exibir resumo explicativo</label>
              </div>
            </div>
            <!-- Filtro de Severidade -->
            <div class="col-12">
              <label class="form-label">Severidades</label>
              <div class="d-flex gap-3 flex-wrap">
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevInfo" checked> <label class="form-check-label" for="uhmSevInfo">Informação</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevWarn" checked> <label class="form-check-label" for="uhmSevWarn">Atenção</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevAvg" checked> <label class="form-check-label" for="uhmSevAvg">Média</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevHigh" checked> <label class="form-check-label" for="uhmSevHigh">Alta</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevDis" checked> <label class="form-check-label" for="uhmSevDis">Desastre</label></div>
              </div>
            </div>
            <!-- Filtrar/Excluir hosts, problema e tags -->
            <div class="col-12">
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label" for="uhmHostContains">Filtrar hosts (contendo)</label>
                  <input type="text" class="form-control" id="uhmHostContains" placeholder="Parte do nome do host"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label" for="uhmExcludeHosts">Excluir hosts (contendo)</label>
                  <input type="text" class="form-control" id="uhmExcludeHosts" placeholder="Lista separada por vírgula"/>
                </div>
              </div>
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label" for="uhmTriggerContains">Filtrar problema (contendo)</label>
                  <input type="text" class="form-control" id="uhmTriggerContains" placeholder="Parte do nome do problema"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label" for="uhmExcludeTriggers">Excluir problema (contendo)</label>
                  <input type="text" class="form-control" id="uhmExcludeTriggers" placeholder="Lista separada por vírgula"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label" for="uhmTagsInclude">Filtrar tags (contendo)</label>
                  <input type="text" class="form-control" id="uhmTagsInclude" placeholder="ex: service:web, env:prod"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label" for="uhmTagsExclude">Excluir tags (contendo)</label>
                  <input type="text" class="form-control" id="uhmTagsExclude" placeholder="Lista separada por vírgula"/>
                </div>
              </div>
            </div>
            <!-- Filtro de ACK -->
            <div class="col-md-4">
              <label class="form-label" for="uhmAckFilter">Filtro de ACK</label>
              <select class="form-select" id="uhmAckFilter">
                <option value="all">Todos</option>
                <option value="only_acked">Somente com ACK</option>
                <option value="only_unacked">Somente sem ACK</option>
              </select>
            </div>
            <!-- Paleta de cores -->
            <div class="col-md-6">
              <label class="form-label" for="uhmPalette">Paleta de cores</label>
              <select class="form-select" id="uhmPalette">
                <option value="OrRd">OrRd (Laranja/Vermelho)</option>
                <option value="Reds">Reds</option>
                <option value="YlOrRd">YlOrRd</option>
                <option value="PuRd">PuRd</option>
                <option value="viridis">Viridis</option>
                <option value="plasma">Plasma</option>
              </select>
            </div>
            <!-- Anotar contagens nas células -->
            <div class="col-md-6 form-check d-flex align-items-end">
              <div>
                <input class="form-check-input" type="checkbox" id="uhmAnnotate" checked>
                <label class="form-check-label" for="uhmAnnotate">Anotar contagens nas células</label>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveUhmBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeUhmModal');
  }
})();

