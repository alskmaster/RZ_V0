(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['root_cause_top_triggers'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureRCTTModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('rcttTitle'),
        topN: document.getElementById('rcttTopN'),
        sortBy: document.getElementById('rcttSortBy'),
        hostContains: document.getElementById('rcttHostContains'),
        periodSubFilter: document.getElementById('rcttPeriodSubFilter'),
        sevInfo: document.getElementById('rcttSevInfo'),
        sevWarn: document.getElementById('rcttSevWarn'),
        sevAvg: document.getElementById('rcttSevAvg'),
        sevHigh: document.getElementById('rcttSevHigh'),
        sevDis: document.getElementById('rcttSevDis'),
        showTable: document.getElementById('rcttShowTable'),
        saveBtn: document.getElementById('saveRCTTBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.topN.value = o.top_n || 5;
      el.sortBy.value = o.sort_by || 'count';
      el.hostContains.value = o.host_name_contains || '';
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.showTable.checked = (o.show_table !== false);
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
        top_n: parseInt(el.topN.value || '5', 10),
        sort_by: el.sortBy.value || 'count',
        host_name_contains: el.hostContains.value || null,
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        severities: severities.length ? severities : ['info','warning','average','high','disaster'],
        show_table: !!el.showTable.checked,
      };
    }
  };

  function ensureRCTTModal(){
    let el = document.getElementById('customizeRCTTModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeRCTTModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Causa-Raiz (Top Gatilhos)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="rcttTitle">Título do módulo</label>
              <input type="text" class="form-control" id="rcttTitle" placeholder="Ex: Top 5 Gatilhos"/>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="rcttTopN">Top N</label>
              <input type="number" class="form-control" id="rcttTopN" min="1" value="5"/>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="rcttSortBy">Ordenar por</label>
              <select class="form-select" id="rcttSortBy">
                <option value="count">Ocorrencias</option>
                <option value="downtime">Downtime</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="rcttHostContains">Host (contém)</label>
              <input type="text" class="form-control" id="rcttHostContains" placeholder="Parte do nome do host"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="rcttPeriodSubFilter">Período (Sub-filtro)</label>
              <select class="form-select" id="rcttPeriodSubFilter">
                <option value="full_month">Mês completo</option>
                <option value="last_24h">Últimas 24h</option>
                <option value="last_7d">Últimos 7 dias</option>
              </select>
            </div>
            <div class="col-12">
              <label class="form-label">Severidades</label>
              <div class="d-flex gap-3 flex-wrap">
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rcttSevInfo" checked> <label class="form-check-label" for="rcttSevInfo">Informação</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rcttSevWarn" checked> <label class="form-check-label" for="rcttSevWarn">Atenção</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rcttSevAvg" checked> <label class="form-check-label" for="rcttSevAvg">Média</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rcttSevHigh" checked> <label class="form-check-label" for="rcttSevHigh">Alta</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="rcttSevDis" checked> <label class="form-check-label" for="rcttSevDis">Desastre</label></div>
              </div>
            </div>
            <div class="col-12 form-check pt-2">
              <input class="form-check-input" type="checkbox" id="rcttShowTable" checked>
              <label class="form-check-label" for="rcttShowTable">Exibir tabela resumo</label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveRCTTBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeRCTTModal');
  }
})();

