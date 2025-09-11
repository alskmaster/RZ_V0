(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['mttr'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureMTTRModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('mttrTitle'),
        periodSubFilter: document.getElementById('mttrPeriodSubFilter'),
        // Filtros
        hostContains: document.getElementById('mttrHostContains'),
        excludeHosts: document.getElementById('mttrExcludeHosts'),
        triggerContains: document.getElementById('mttrTriggerContains'),
        excludeTriggers: document.getElementById('mttrExcludeTriggers'),
        tagsInclude: document.getElementById('mttrTagsInclude'),
        tagsExclude: document.getElementById('mttrTagsExclude'),
        ackFilter: document.getElementById('mttrAckFilter'),
        // Severidades
        sevInfo: document.getElementById('mttrSevInfo'),
        sevWarn: document.getElementById('mttrSevWarn'),
        sevAvg: document.getElementById('mttrSevAvg'),
        sevHigh: document.getElementById('mttrSevHigh'),
        sevDis: document.getElementById('mttrSevDis'),
        // Resumo
        showSummary: document.getElementById('mttrShowSummary'),
        // Ação
        saveBtn: document.getElementById('saveMTTRBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.hostContains.value = o.host_name_contains || '';
      if (el.excludeHosts) el.excludeHosts.value = o.exclude_hosts_contains || '';
      if (el.triggerContains) el.triggerContains.value = o.trigger_name_contains || '';
      if (el.excludeTriggers) el.excludeTriggers.value = o.exclude_triggers_contains || '';
      if (el.tagsInclude) el.tagsInclude.value = o.tags_include || '';
      if (el.tagsExclude) el.tagsExclude.value = o.tags_exclude || '';
      if (el.ackFilter) el.ackFilter.value = o.ack_filter || (o.only_acknowledged ? 'only_acked' : 'all');
      if (el.showSummary) el.showSummary.checked = (o.show_summary !== false);

      const sel = new Set(o.severities || ['info','warning','average','high','disaster']);
      el.sevInfo.checked = sel.has('info');
      el.sevWarn.checked = sel.has('warning');
      el.sevAvg.checked = sel.has('average');
      el.sevHigh.checked = sel.has('high');
      el.sevDis.checked = sel.has('disaster');
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements; const severities = [];
      if (el.sevInfo.checked) severities.push('info');
      if (el.sevWarn.checked) severities.push('warning');
      if (el.sevAvg.checked) severities.push('average');
      if (el.sevHigh.checked) severities.push('high');
      if (el.sevDis.checked) severities.push('disaster');
      return {
        __title: el.title.value || '',
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        severities: severities.length ? severities : ['info','warning','average','high','disaster'],
        host_name_contains: el.hostContains.value || null,
        exclude_hosts_contains: el.excludeHosts ? (el.excludeHosts.value || null) : null,
        trigger_name_contains: el.triggerContains ? (el.triggerContains.value || null) : null,
        exclude_triggers_contains: el.excludeTriggers ? (el.excludeTriggers.value || null) : null,
        tags_include: el.tagsInclude ? (el.tagsInclude.value || null) : null,
        tags_exclude: el.tagsExclude ? (el.tagsExclude.value || null) : null,
        ack_filter: el.ackFilter ? (el.ackFilter.value || 'all') : 'all',
        show_summary: el.showSummary ? !!el.showSummary.checked : true
      };
    }
  };

  function ensureMTTRModal(){
    let el = document.getElementById('customizeMTTRModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeMTTRModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: MTTR / MTTD</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <!-- Título do módulo -->
            <div class="col-12">
              <label class="form-label" for="mttrTitle">Título do módulo</label>
              <input type="text" class="form-control" id="mttrTitle" placeholder="Ex: Eficiência da Resposta (MTTR)"/>
            </div>
            <!-- Filtro de Período -->
            <div class="col-md-4">
              <label class="form-label" for="mttrPeriodSubFilter">Período</label>
              <select class="form-select" id="mttrPeriodSubFilter">
                <option value="full_month">Mês Completo</option>
                <option value="last_7d">Últimos 7 dias</option>
                <option value="last_24h">Últimas 24h</option>
              </select>
            </div>
            <!-- Opção de Exibir Resumo/Dica -->
            <div class="col-md-4 form-check d-flex align-items-end">
              <div>
                <input class="form-check-input" type="checkbox" id="mttrShowSummary" checked>
                <label class="form-check-label" for="mttrShowSummary">Exibir resumo/dica</label>
              </div>
            </div>
            <!-- Filtro de Severidade -->
            <div class="col-12">
              <label class="form-label">Severidades</label>
              <div class="d-flex gap-3 flex-wrap">
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevInfo" checked> <label class="form-check-label" for="mttrSevInfo">Informação</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevWarn" checked> <label class="form-check-label" for="mttrSevWarn">Atenção</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevAvg" checked> <label class="form-check-label" for="mttrSevAvg">Média</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevHigh" checked> <label class="form-check-label" for="mttrSevHigh">Alta</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevDis" checked> <label class="form-check-label" for="mttrSevDis">Desastre</label></div>
              </div>
            </div>
            <!-- Filtrar/Excluir host, problema e tags -->
            <div class="col-12">
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label" for="mttrHostContains">Filtrar hosts (contendo)</label>
                  <input type="text" class="form-control" id="mttrHostContains" placeholder="Parte do nome do host"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label" for="mttrExcludeHosts">Excluir hosts (contendo)</label>
                  <input type="text" class="form-control" id="mttrExcludeHosts" placeholder="Lista separada por vírgula"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label" for="mttrTriggerContains">Filtrar problema (contendo)</label>
                  <input type="text" class="form-control" id="mttrTriggerContains" placeholder="Parte do nome do problema"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label" for="mttrExcludeTriggers">Excluir problema (contendo)</label>
                  <input type="text" class="form-control" id="mttrExcludeTriggers" placeholder="Lista separada por vírgula"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label" for="mttrTagsInclude">Filtrar tags (contendo)</label>
                  <input type="text" class="form-control" id="mttrTagsInclude" placeholder="ex: service:web, env:prod"/>
                </div>
                <div class="col-md-6">
                  <label class="form-label" for="mttrTagsExclude">Excluir tags (contendo)</label>
                  <input type="text" class="form-control" id="mttrTagsExclude" placeholder="Lista separada por vírgula"/>
                </div>
              </div>
            </div>
            <!-- Filtro de ACK -->
            <div class="col-md-4">
              <label class="form-label" for="mttrAckFilter">Filtro de ACK</label>
              <select class="form-select" id="mttrAckFilter">
                <option value="all">Todos</option>
                <option value="only_acked">Somente com ACK</option>
                <option value="only_unacked">Somente sem ACK</option>
              </select>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveMTTRBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeMTTRModal');
  }
})();

