(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['recurring_problems'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureRecurringProblemsModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('rpTitle'),
        minCount: document.getElementById('rpMinCount'),
        hostContains: document.getElementById('rpHostContains'),
        excludeHosts: document.getElementById('rpExcludeHosts'),
        periodSubFilter: document.getElementById('rpPeriodSubFilter'),
        ackFilter: document.getElementById('rpAckFilter'),
        trigContains: document.getElementById('rpTrigContains'),
        exclTrigs: document.getElementById('rpExcludeTrigs'),
        tagsInclude: document.getElementById('rpTagsInclude'),
        tagsExclude: document.getElementById('rpTagsExclude'),
        sevInfo: document.getElementById('rpSevInfo'),
        sevWarn: document.getElementById('rpSevWarn'),
        sevAvg: document.getElementById('rpSevAvg'),
        sevHigh: document.getElementById('rpSevHigh'),
        sevDis: document.getElementById('rpSevDis'),
        saveBtn: document.getElementById('saveRPBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.minCount.value = o.min_count || 3;
      el.hostContains.value = o.host_name_contains || '';
      if (el.excludeHosts) el.excludeHosts.value = o.exclude_hosts_contains || '';
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      if (el.ackFilter) el.ackFilter.value = o.ack_filter || 'all';
      if (el.trigContains) el.trigContains.value = o.trigger_name_contains || '';
      if (el.exclTrigs) el.exclTrigs.value = o.exclude_triggers_contains || '';
      if (el.tagsInclude) el.tagsInclude.value = o.tags_include || '';
      if (el.tagsExclude) el.tagsExclude.value = o.tags_exclude || '';
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
        min_count: parseInt(el.minCount.value || '3', 10),
        host_name_contains: el.hostContains.value || null,
        exclude_hosts_contains: el.excludeHosts ? (el.excludeHosts.value || null) : null,
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        ack_filter: el.ackFilter ? (el.ackFilter.value || 'all') : 'all',
        trigger_name_contains: el.trigContains ? (el.trigContains.value || null) : null,
        exclude_triggers_contains: el.exclTrigs ? (el.exclTrigs.value || null) : null,
        tags_include: el.tagsInclude ? (el.tagsInclude.value || null) : null,
        tags_exclude: el.tagsExclude ? (el.tagsExclude.value || null) : null,
        severities: severities.length ? severities : ['info','warning','average','high','disaster']
      };
    }
  };

  function ensureRecurringProblemsModal(){
    let el = document.getElementById('customizeRecurringProblemsModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeRecurringProblemsModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Problemas Recorrentes</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="rpTitle">Título do módulo</label>
              <input type="text" class="form-control" id="rpTitle" placeholder="Ex: Problemas Recorrentes"/>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="rpMinCount">Ocorrências mínimas</label>
              <input type="number" class="form-control" id="rpMinCount" min="1" value="3"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="rpHostContains">Host (contém)</label>
              <input type="text" class="form-control" id="rpHostContains" placeholder="Parte do nome do host"/>
            </div>
            <details class="gear-advanced mt-2">
              <summary class="gear-advanced-summary">Filtros Avan�ados</summary>
              <div class="row g-3 mt-1">
            <div class="col-md-3">
            <div class="col-md-6">
              <label class="form-label" for="rpExcludeHosts">Excluir hosts (contendo)</label>
              <input type="text" class="form-control" id="rpExcludeHosts" placeholder="ex: teste, lab"/>
            </div>
              <label class="form-label" for="rpPeriodSubFilter">Período (sub-filtro)</label>
              <select class="form-select" id="rpPeriodSubFilter">
                <option value="full_month">Mês completo</option>
                <option value="last_24h">Últimas 24h</option>
                <option value="last_7d">Últimos 7 dias</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="rpAckFilter">Filtro de ACK</label>
              <select class="form-select" id="rpAckFilter"><option value="all">Todos</option><option value="only_acked">Somente com ACK</option><option value="only_unacked">Somente sem ACK</option></select>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="rpTrigContains">Filtro por Trigger (contendo)</label>
              <input type="text" class="form-control" id="rpTrigContains" placeholder="ex: link down"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="rpExcludeTrigs">Excluir Trigger (contendo)</label>
              <input type="text" class="form-control" id="rpExcludeTrigs" placeholder="ex: cpu, memoria"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="rpTagsInclude">Tags (incluir)</label>
              <input type="text" class="form-control" id="rpTagsInclude" placeholder="ex: service:web, env:prod"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="rpTagsExclude">Tags (excluir)</label>
              <input type="text" class="form-control" id="rpTagsExclude" placeholder="ex: env:dev"/>
            </div>
              </div>
            </details>
            <div class="col-12">
              <label class="form-label">Severidades</label>
              <div class="d-flex gap-3 flex-wrap">
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rpSevInfo" checked> <label class="form-check-label" for="rpSevInfo">Informação</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rpSevWarn" checked> <label class="form-check-label" for="rpSevWarn">Atenção</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rpSevAvg" checked> <label class="form-check-label" for="rpSevAvg">Média</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rpSevHigh" checked> <label class="form-check-label" for="rpSevHigh">Alta</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rpSevDis" checked> <label class="form-check-label" for="rpSevDis">Desastre</label></div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveRPBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeRecurringProblemsModal');
  }
})();


