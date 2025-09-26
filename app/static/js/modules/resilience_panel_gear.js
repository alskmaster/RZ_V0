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
        triggerContains: document.getElementById('resPanelTriggerContains'),
        triggerExclude: document.getElementById('resPanelTriggerExclude'),
        tagsInclude: document.getElementById('resPanelTagsInclude'),
        tagsExclude: document.getElementById('resPanelTagsExclude'),
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
        severities: {
          not_classified: document.getElementById('resPanelSevNC'),
          info: document.getElementById('resPanelSevInfo'),
          warning: document.getElementById('resPanelSevWarn'),
          average: document.getElementById('resPanelSevAvg'),
          high: document.getElementById('resPanelSevHigh'),
          disaster: document.getElementById('resPanelSevDis')
        },
        saveBtn: document.getElementById('saveResiliencePanelBtn')
      };
    },
    load(options){
      this._ensure();
      const o = options || {};
      const el = this.elements;
      try {
        const curr = window.currentModuleToCustomize || null;
        el.titleInput.value = (curr && curr.title) ? String(curr.title) : '';
      } catch (err) {
        el.titleInput.value = '';
      }
      el.hostContains.value = o.host_name_contains || '';
      el.hostExclude.value = o.exclude_hosts_contains || '';
      el.triggerContains.value = o.trigger_contains || '';
      el.triggerExclude.value = o.trigger_exclude || '';
      el.tagsInclude.value = o.tags_include || '';
      el.tagsExclude.value = o.tags_exclude || '';
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
      const defaultSeverities = ['not_classified','info','warning','average','high','disaster'];
      const selected = new Set(Array.isArray(o.severities) && o.severities.length ? o.severities : defaultSeverities);
      Object.entries(el.severities).forEach(([key, checkbox]) => {
        if (checkbox) checkbox.checked = selected.has(key);
      });
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', () => {
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once: true });
    },
    save(){
      const el = this.elements;
      const severityEntries = Object.entries(el.severities)
        .filter(([, checkbox]) => checkbox && checkbox.checked)
        .map(([key]) => key);
      return {
        __title: el.titleInput.value || '',
        host_name_contains: el.hostContains.value || null,
        exclude_hosts_contains: el.hostExclude.value || null,
        trigger_contains: el.triggerContains.value || null,
        trigger_exclude: el.triggerExclude.value || null,
        tags_include: el.tagsInclude.value || null,
        tags_exclude: el.tagsExclude.value || null,
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
        severities: severityEntries.length ? severityEntries : ['not_classified','info','warning','average','high','disaster']
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
          <h5 class="modal-title">Personalizar Modulo: Painel de Resiliencia (SLA Preciso)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="resPanelTitle">Titulo do modulo</label>
              <input type="text" class="form-control" id="resPanelTitle" placeholder="Ex: Painel de Resiliencia" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="resPanelHostContains">Filtrar hosts (contendo)</label>
              <input type="text" class="form-control" id="resPanelHostContains" placeholder="Parte do nome do host" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="resPanelHostExclude">Excluir hosts (contendo)</label>
              <input type="text" class="form-control" id="resPanelHostExclude" placeholder="Lista separada por virgula" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="resPanelTriggerContains">Filtrar triggers (contendo)</label>
              <input type="text" class="form-control" id="resPanelTriggerContains" placeholder="Ex: SLA, ping" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="resPanelTriggerExclude">Excluir triggers (contendo)</label>
              <input type="text" class="form-control" id="resPanelTriggerExclude" placeholder="Ex: manutencao" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="resPanelTagsInclude">Filtrar tags (contendo)</label>
              <input type="text" class="form-control" id="resPanelTagsInclude" placeholder="Ex: service:web" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="resPanelTagsExclude">Excluir tags (contendo)</label>
              <input type="text" class="form-control" id="resPanelTagsExclude" placeholder="Ex: scope:test" />
            </div>
            <div class="col-12">
              <span class="fw-semibold d-block">Severidades consideradas</span>
              <div class="d-flex flex-wrap gap-3 mt-2">
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="resPanelSevNC" checked>
                  <label class="form-check-label" for="resPanelSevNC">Nao classificado</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="resPanelSevInfo" checked>
                  <label class="form-check-label" for="resPanelSevInfo">Info</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="resPanelSevWarn" checked>
                  <label class="form-check-label" for="resPanelSevWarn">Warning</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="resPanelSevAvg" checked>
                  <label class="form-check-label" for="resPanelSevAvg">Average</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="resPanelSevHigh" checked>
                  <label class="form-check-label" for="resPanelSevHigh">High</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="resPanelSevDis" checked>
                  <label class="form-check-label" for="resPanelSevDis">Disaster</label>
                </div>
              </div>
              <small class="text-muted">Desmarque severidades que nao devem impactar o calculo.</small>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelPeriodSubFilter">Periodo</label>
              <select class="form-select" id="resPanelPeriodSubFilter">
                <option value="full_month">Mes completo</option>
                <option value="last_7d">Ultimos 7 dias</option>
                <option value="last_24h">Ultimas 24h</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelDecimals">Casas decimais (SLA %)</label>
              <input type="number" class="form-control" id="resPanelDecimals" min="0" max="6" value="2" />
            </div>
            <div class="col-md-4 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resPanelHighlight" checked>
              <label class="form-check-label" for="resPanelHighlight">Destacar abaixo da meta</label>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelOrderBy">Ordenar por</label>
              <select class="form-select" id="resPanelOrderBy">
                <option value="sla">SLA (%)</option>
                <option value="downtime">Downtime (s)</option>
                <option value="host">Host</option>
              </select>
            </div>
            <div class="col-md-4 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resPanelOrderAsc" checked>
              <label class="form-check-label" for="resPanelOrderAsc">Ascendente</label>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelTopN">Top N</label>
              <input type="number" class="form-control" id="resPanelTopN" min="1" placeholder="Opcional" />
            </div>
            <div class="col-md-4 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resPanelShowChart">
              <label class="form-check-label" for="resPanelShowChart">Exibir grafico por host</label>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelChartColor">Cor das barras</label>
              <input type="color" class="form-control form-control-color" id="resPanelChartColor" value="#4e79a7" />
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelBelowColor">Cor abaixo da meta</label>
              <input type="color" class="form-control form-control-color" id="resPanelBelowColor" value="#e15759" />
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

