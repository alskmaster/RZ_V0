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
        topNTable: document.getElementById('rcttTopNTable'),
        topNChart: document.getElementById('rcttTopNChart'),
        sortBy: document.getElementById('rcttSortBy'),
        sortAsc: document.getElementById('rcttSortAsc'),
        triggerContains: document.getElementById('rcttTriggerContains'),
        excludeTriggersContains: document.getElementById('rcttExcludeTriggersContains'),
        periodSubFilter: document.getElementById('rcttPeriodSubFilter'),
        sevInfo: document.getElementById('rcttSevInfo'),
        sevWarn: document.getElementById('rcttSevWarn'),
        sevAvg: document.getElementById('rcttSevAvg'),
        sevHigh: document.getElementById('rcttSevHigh'),
        sevDis: document.getElementById('rcttSevDis'),
        showTable: document.getElementById('rcttShowTable'),
        showChart: document.getElementById('rcttShowChart'),
        maxLabelLen: document.getElementById('rcttMaxLabelLen'),
        showValues: document.getElementById('rcttShowValues'),
        saveBtn: document.getElementById('saveRCTTBtn')
      };
      // Oculta campos antigos baseados em Host, se existirem (compatibilidade visual)
      try {
        const oldHost = document.getElementById('rcttHostContains');
        if (oldHost && oldHost.closest) {
          const wrap = oldHost.closest('.col-md-6') || oldHost.parentElement;
          if (wrap) wrap.style.display = 'none';
        }
        const oldExclHost = document.getElementById('rcttExcludeHostsContains');
        if (oldExclHost && oldExclHost.closest) {
          const wrap2 = oldExclHost.closest('.col-12') || oldExclHost.parentElement;
          if (wrap2) wrap2.style.display = 'none';
        }
      } catch (e) { /* noop */ }
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      const tn = parseInt(o.top_n, 10) || 5;
      el.topNTable.value = (o.top_n_table != null ? o.top_n_table : tn);
      el.topNChart.value = (o.top_n_chart != null ? o.top_n_chart : tn);
      el.sortBy.value = o.sort_by || 'count';
      el.sortAsc.checked = !!o.sort_asc;
      el.triggerContains.value = (o.trigger_name_contains || o.host_name_contains || '');
      el.excludeTriggersContains.value = (o.exclude_triggers_contains || o.exclude_hosts_contains || '');
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.showTable.checked = (o.show_table !== false);
      el.showChart.checked = (o.show_chart !== false);
      el.maxLabelLen.value = (o.max_label_len != null ? o.max_label_len : 48);
      el.showValues.checked = (o.show_values !== false);
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
        top_n: parseInt((el.topNTable.value || el.topNChart.value || '5'), 10),
        top_n_table: parseInt(el.topNTable.value || '5', 10),
        top_n_chart: parseInt(el.topNChart.value || '5', 10),
        sort_by: el.sortBy.value || 'count',
        sort_asc: !!el.sortAsc.checked,
        trigger_name_contains: el.triggerContains.value || null,
        exclude_triggers_contains: el.excludeTriggersContains.value || null,
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        severities: severities.length ? severities : ['info','warning','average','high','disaster'],
        show_table: !!el.showTable.checked,
        show_chart: !!el.showChart.checked,
        max_label_len: parseInt(el.maxLabelLen.value || '48', 10),
        show_values: !!el.showValues.checked,
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
              <label class="form-label" for="rcttTopNTable">Top N (Tabela)</label>
              <input type="number" class="form-control" id="rcttTopNTable" min="0" value="5"/>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="rcttTopNChart">Top N (Grafico)</label>
              <input type="number" class="form-control" id="rcttTopNChart" min="0" value="5"/>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="rcttSortBy">Ordenar por</label>
              <select class="form-select" id="rcttSortBy">
                <option value="count">Ocorrencias</option>
                <option value="downtime">Downtime</option>
              </select>
            </div>
            <div class="col-md-3 form-check d-flex align-items-end">
              <div>
                <input class="form-check-input" type="checkbox" id="rcttSortAsc">
                <label class="form-check-label" for="rcttSortAsc">Ordem ascendente</label>
              </div>
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
            <div class="col-12 form-check">
              <input class="form-check-input" type="checkbox" id="rcttShowChart" checked>
              <label class="form-check-label" for="rcttShowChart">Exibir gráfico</label>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="rcttMaxLabelLen">Tamanho máx. do rótulo</label>
              <input type="number" class="form-control" id="rcttMaxLabelLen" min="10" value="48"/>
            </div>
            <div class="col-md-3 form-check d-flex align-items-end">
              <div>
                <input class="form-check-input" type="checkbox" id="rcttShowValues" checked>
                <label class="form-check-label" for="rcttShowValues">Mostrar valores no gráfico</label>
              </div>
            </div>
            <div class="col-12">
              <label class="form-label" for="rcttTriggerContains">Trigger (contém)</label>
              <input type="text" class="form-control" id="rcttTriggerContains" placeholder="Parte do nome do trigger"/>
            </div>
            <div class="col-12">
              <label class="form-label" for="rcttExcludeTriggersContains">Excluir Triggers (contém, vírgulas)</label>
              <input type="text" class="form-control" id="rcttExcludeTriggersContains" placeholder="ex.: ping,link,backup"/>
            </div>
            <div class="col-12">
              <label class="form-label" for="rcttExcludeHostsContains">Excluir Hosts (contém, vírgulas)</label>
              <input type="text" class="form-control" id="rcttExcludeHostsContains" placeholder="ex.: lab,dev,backup"/>
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
    const modalRoot = document.getElementById('customizeRCTTModal');
    // Remocao fisica de campos antigos baseados em Host, se ainda existirem no HTML gerado
    try {
      const hostInput = modalRoot.querySelector('#rcttHostContains');
      if (hostInput) {
        const hostWrap = hostInput.closest('.col-md-6') || hostInput.parentElement;
        if (hostWrap && hostWrap.parentElement) hostWrap.parentElement.removeChild(hostWrap);
      }
      const exclHostInput = modalRoot.querySelector('#rcttExcludeHostsContains');
      if (exclHostInput) {
        const exclWrap = exclHostInput.closest('.col-12') || exclHostInput.parentElement;
        if (exclWrap && exclWrap.parentElement) exclWrap.parentElement.removeChild(exclWrap);
      }
    } catch(e) { /* noop */ }
    return modalRoot;
  }
})();

