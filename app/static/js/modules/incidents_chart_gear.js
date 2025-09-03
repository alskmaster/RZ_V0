(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['incidents_chart'] = {
    _ensure(){
      const el = ensureIncidentsChartModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        severityInfo: el.querySelector('#incChSeverityInfo'),
        severityWarning: el.querySelector('#incChSeverityWarning'),
        severityAverage: el.querySelector('#incChSeverityAverage'),
        severityHigh: el.querySelector('#incChSeverityHigh'),
        severityDisaster: el.querySelector('#incChSeverityDisaster'),
        periodSubFilter: el.querySelector('#incChPeriodSubFilter'),
        chartType: el.querySelector('#incChChartType'),
        problemTypeTopN: el.querySelector('#incChProblemTypeTopN'),
        dailyType: el.querySelector('#incChDailyType'),
        dailySev: el.querySelector('#incChDailySev'),
        xRotate: el.querySelector('#incChXRotate'),
        xAlternate: el.querySelector('#incChXAlternate'),
        saveBtn: el.querySelector('#saveIncChCustomizationBtn')
      };
    },
    load(opts){
      this._ensure();
      const o = opts || {}; const el = this.elements;
      const def = ['info','warning','average','high','disaster'];
      const sel = o.severities || def;
      el.severityInfo.checked = sel.includes('info');
      el.severityWarning.checked = sel.includes('warning');
      el.severityAverage.checked = sel.includes('average');
      el.severityHigh.checked = sel.includes('high');
      el.severityDisaster.checked = sel.includes('disaster');
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.chartType.value = o.chart_type || 'severity_pie';
      el.problemTypeTopN.value = o.problem_type_top_n || '';
      el.dailyType.value = o.daily_volume_chart_type || 'bar';
      Array.from(el.dailySev.options).forEach(opt => { opt.selected = (o.daily_volume_severities||[]).includes(opt.value); });
      el.xRotate.checked = o.x_axis_rotate_labels !== false;
      el.xAlternate.checked = o.x_axis_alternate_days !== false;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements; const severities = [];
      if (el.severityInfo.checked) severities.push('info');
      if (el.severityWarning.checked) severities.push('warning');
      if (el.severityAverage.checked) severities.push('average');
      if (el.severityHigh.checked) severities.push('high');
      if (el.severityDisaster.checked) severities.push('disaster');
      const dailySev = Array.from(el.dailySev.selectedOptions).map(o=>o.value);
      return {
        severities,
        period_sub_filter: el.periodSubFilter.value,
        chart_type: el.chartType.value,
        problem_type_top_n: el.problemTypeTopN.value ? parseInt(el.problemTypeTopN.value) : null,
        daily_volume_chart_type: el.dailyType.value,
        daily_volume_severities: dailySev,
        x_axis_rotate_labels: !!el.xRotate.checked,
        x_axis_alternate_days: !!el.xAlternate.checked,
      };
    }
  };

  function ensureIncidentsChartModal(){
    let el = document.getElementById('customizeIncChModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeIncChModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Incidentes (Gráficos)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body"><div class="row">
          <div class="col-md-6">
            <label class="form-label">Severidades</label>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incChSeverityInfo"><label class="form-check-label" for="incChSeverityInfo">Informação</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incChSeverityWarning"><label class="form-check-label" for="incChSeverityWarning">Atenção</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incChSeverityAverage"><label class="form-check-label" for="incChSeverityAverage">Média</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incChSeverityHigh"><label class="form-check-label" for="incChSeverityHigh">Alta</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incChSeverityDisaster"><label class="form-check-label" for="incChSeverityDisaster">Desastre</label></div>
            <div class="mb-3"><label class="form-label" for="incChPeriodSubFilter">Período</label>
              <select class="form-select" id="incChPeriodSubFilter">
                <option value="full_month">Mês Completo</option>
                <option value="last_24h">Últimas 24h</option>
                <option value="last_7d">Últimos 7 dias</option>
              </select>
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3"><label class="form-label" for="incChChartType">Tipo de Gráfico</label>
              <select class="form-select" id="incChChartType">
                <option value="severity_pie">Pizza por Severidade</option>
                <option value="severity_bar">Barras por Severidade</option>
                <option value="problem_type_bar">Top Tipos de Problema</option>
                <option value="daily_volume">Volume Diário</option>
                <option value="daily_volume_severity">Volume Diário (por Severidade)</option>
              </select>
            </div>
            <div class="mb-3"><label class="form-label" for="incChProblemTypeTopN">Top N (Tipos de Problema)</label>
              <input type="number" class="form-control" id="incChProblemTypeTopN" min="1" placeholder="10"></div>
            <div class="mb-3"><label class="form-label" for="incChDailyType">Volume Diário: Estilo</label>
              <select class="form-select" id="incChDailyType"><option value="bar">Barras</option><option value="line">Linhas</option></select>
            </div>
            <div class="mb-3"><label class="form-label" for="incChDailySev">Severidades (para Volume Diário por Severidade)</label>
              <select class="form-select" id="incChDailySev" multiple size="5">
                <option value="info">Informação</option>
                <option value="warning">Atenção</option>
                <option value="average">Média</option>
                <option value="high">Alta</option>
                <option value="disaster">Desastre</option>
              </select>
            </div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incChXRotate" checked><label class="form-check-label" for="incChXRotate">Rotacionar rótulos do eixo X</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incChXAlternate" checked><label class="form-check-label" for="incChXAlternate">Dias alternados no eixo X</label></div>
          </div>
        </div></div>
        <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveIncChCustomizationBtn">Salvar Personalização</button></div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeIncChModal');
  }
})();
