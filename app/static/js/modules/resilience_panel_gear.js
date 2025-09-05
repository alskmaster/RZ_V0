(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['resilience_panel'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureResiliencePanelModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        titleInput: document.getElementById('resPanelTitle'),
        hostContains: document.getElementById('resPanelHostContains'),
        hostExclude: document.getElementById('resPanelHostExclude'),
        periodSubFilter: document.getElementById('resPanelPeriodSubFilter'),
        decimals: document.getElementById('resPanelDecimals'),
        highlight: document.getElementById('resPanelHighlight'),
        orderBy: document.getElementById('resPanelOrderBy'),
        orderAsc: document.getElementById('resPanelOrderAsc'),
        topN: document.getElementById('resPanelTopN'),
        showChart: document.getElementById('resPanelShowChart'),
        chartColor: document.getElementById('resPanelChartColor'),
        belowColor: document.getElementById('resPanelBelowColor'),
        xAxis0100: document.getElementById('resPanelXAxis0100'),
        saveBtn: document.getElementById('saveResiliencePanelBtn')
      };
    },
    load(o){
      this._ensure();
      o = o || {}; const el = this.elements;
      try {
        const curr = window.currentModuleToCustomize || null;
        el.titleInput.value = (curr && curr.title) ? String(curr.title) : '';
      } catch(e) { el.titleInput.value = ''; }
      el.hostContains.value = o.host_name_contains || '';
      if (el.hostExclude) el.hostExclude.value = o.exclude_hosts_contains || '';
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.decimals.value = (o.decimals ?? 2);
      el.highlight.checked = (o.highlight_below_goal !== false);
      if (el.orderBy) el.orderBy.value = o.sort_by || 'sla';
      if (el.orderAsc) el.orderAsc.checked = (o.sort_asc !== false);
      if (el.topN) el.topN.value = o.top_n || '';
      if (el.showChart) el.showChart.checked = (o.show_chart === true);
      if (el.chartColor) el.chartColor.value = o.chart_color || '#4e79a7';
      if (el.belowColor) el.belowColor.value = o.below_color || '#e15759';
      if (el.xAxis0100) el.xAxis0100.checked = (o.x_axis_0_100 === true);
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      return {
        __title: el.titleInput.value || '',
        host_name_contains: el.hostContains.value || null,
        exclude_hosts_contains: el.hostExclude ? (el.hostExclude.value || null) : null,
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        decimals: el.decimals.value ? parseInt(el.decimals.value, 10) : 2,
        highlight_below_goal: !!el.highlight.checked,
        sort_by: el.orderBy ? (el.orderBy.value || 'sla') : 'sla',
        sort_asc: el.orderAsc ? !!el.orderAsc.checked : true,
        top_n: el.topN && el.topN.value ? parseInt(el.topN.value, 10) : null,
        show_chart: el.showChart ? !!el.showChart.checked : false,
        chart_color: el.chartColor ? (el.chartColor.value || '#4e79a7') : '#4e79a7',
        below_color: el.belowColor ? (el.belowColor.value || '#e15759') : '#e15759',
        x_axis_0_100: el.xAxis0100 ? !!el.xAxis0100.checked : false,
      };
    }
  };

  function ensureResiliencePanelModal(){
    let el = document.getElementById('customizeResiliencePanelModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeResiliencePanelModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Personalizar Módulo: Painel de Resiliência (SLA Preciso)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="resPanelTitle">Título do módulo</label>
              <input type="text" class="form-control" id="resPanelTitle" placeholder="Ex: Painel de Resiliência (SLA Preciso)"/>
            </div>
            <div class="col-md-8">
              <label class="form-label" for="resPanelHostContains">Host (contém)</label>
              <input type="text" class="form-control" id="resPanelHostContains" placeholder="Parte do nome do host"/>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelPeriodSubFilter">Período (Sub-filtro)</label>
              <select class="form-select" id="resPanelPeriodSubFilter">
                <option value="full_month">Mês completo</option>
                <option value="last_24h">Últimas 24h</option>
                <option value="last_7d">Últimos 7 dias</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelDecimals">Casas decimais (SLA %)</label>
              <input type="number" class="form-control" id="resPanelDecimals" min="0" max="6" value="2"/>
            </div>
            <div class="col-md-4 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resPanelHighlight" checked>
              <label class="form-check-label" for="resPanelHighlight">Destacar abaixo da meta</label>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="resPanelHostExclude">Excluir hosts (contém)</label>
              <input type="text" class="form-control" id="resPanelHostExclude" placeholder="Lista separada por vírgula"/>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelOrderBy">Ordenar por</label>
              <select class="form-select" id="resPanelOrderBy">
                <option value="sla">SLA (%)</option>
                <option value="downtime">Downtime (s)</option>
                <option value="host">Host</option>
              </select>
            </div>
            <div class="col-md-2 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resPanelOrderAsc" checked>
              <label class="form-check-label" for="resPanelOrderAsc">Ascendente</label>
            </div>
            <div class="col-md-2">
              <label class="form-label" for="resPanelTopN">Top N</label>
              <input type="number" class="form-control" id="resPanelTopN" min="1" placeholder="Opcional"/>
            </div>
            <div class="col-md-4 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resPanelShowChart">
              <label class="form-check-label" for="resPanelShowChart">Exibir gráfico por host</label>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelChartColor">Cor das barras</label>
              <input type="color" class="form-control form-control-color" id="resPanelChartColor" value="#4e79a7"/>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelBelowColor">Cor abaixo da meta</label>
              <input type="color" class="form-control form-control-color" id="resPanelBelowColor" value="#e15759"/>
            </div>
            <div class="col-md-4 form-check">
              <input class="form-check-input" type="checkbox" id="resPanelXAxis0100">
              <label class="form-check-label" for="resPanelXAxis0100">Eixo X de 0 a 100</label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveResiliencePanelBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeResiliencePanelModal');
  }
})();

