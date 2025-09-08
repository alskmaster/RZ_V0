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
        problemTypeKey: el.querySelector('#incChProblemTypeKey'),
        dailyType: el.querySelector('#incChDailyType'),
        dailySev: el.querySelector('#incChDailySev'),
        timeGran: el.querySelector('#incChTimeGranularity'),
        trigContains: el.querySelector('#incChTriggerContains'),
        exclTrigs: el.querySelector('#incChExcludeTriggers'),
        hostContains: el.querySelector('#incChHostContains'),
        exclHosts: el.querySelector('#incChExcludeHosts'),
        tagsInclude: el.querySelector('#incChTagsInclude'),
        tagsExclude: el.querySelector('#incChTagsExclude'),
        ackFilter: el.querySelector('#incChAckFilter'),
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
      if (el.severityInfo) el.severityInfo.checked = sel.includes('info');
      if (el.severityWarning) el.severityWarning.checked = sel.includes('warning');
      if (el.severityAverage) el.severityAverage.checked = sel.includes('average');
      if (el.severityHigh) el.severityHigh.checked = sel.includes('high');
      if (el.severityDisaster) el.severityDisaster.checked = sel.includes('disaster');
      if (el.periodSubFilter) el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      if (el.chartType) el.chartType.value = o.chart_type || 'severity_pie';
      if (el.problemTypeTopN) el.problemTypeTopN.value = (o.problem_type_top_n != null ? o.problem_type_top_n : '');
      if (el.problemTypeKey) el.problemTypeKey.value = o.problem_type_key || 'triggerid';
      if (el.dailyType) el.dailyType.value = o.daily_volume_chart_type || 'bar';
      // Unificado: o conjunto de severidades global vale para todos os gráficos
      if (el.timeGran) el.timeGran.value = o.time_granularity || 'D';
      if (el.trigContains) el.trigContains.value = o.trigger_name_contains || '';
      if (el.exclTrigs) el.exclTrigs.value = o.exclude_triggers_contains || '';
      if (el.hostContains) el.hostContains.value = o.host_name_contains || '';
      if (el.exclHosts) el.exclHosts.value = o.exclude_hosts_contains || '';
      if (el.tagsInclude) el.tagsInclude.value = o.tags_include || '';
      if (el.tagsExclude) el.tagsExclude.value = o.tags_exclude || '';
      if (el.ackFilter) el.ackFilter.value = o.ack_filter || 'all';
      if (el.xRotate) el.xRotate.checked = o.x_axis_rotate_labels !== false;
      if (el.xAlternate) el.xAlternate.checked = o.x_axis_alternate_days !== false;
      el.saveBtn && el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements; const severities = [];
      if (el.severityInfo && el.severityInfo.checked) severities.push('info');
      if (el.severityWarning && el.severityWarning.checked) severities.push('warning');
      if (el.severityAverage && el.severityAverage.checked) severities.push('average');
      if (el.severityHigh && el.severityHigh.checked) severities.push('high');
      if (el.severityDisaster && el.severityDisaster.checked) severities.push('disaster');
      // Unificado: reutiliza as mesmas severidades globais
      const dailySev = severities.slice();
      return {
        severities,
        period_sub_filter: el.periodSubFilter ? el.periodSubFilter.value : 'full_month',
        chart_type: el.chartType ? el.chartType.value : 'severity_pie',
        problem_type_top_n: (el.problemTypeTopN && el.problemTypeTopN.value) ? parseInt(el.problemTypeTopN.value) : null,
        problem_type_key: el.problemTypeKey ? el.problemTypeKey.value : 'triggerid',
        daily_volume_chart_type: el.dailyType ? el.dailyType.value : 'bar',
        daily_volume_severities: dailySev,
        time_granularity: el.timeGran ? el.timeGran.value : 'D',
        trigger_name_contains: el.trigContains ? (el.trigContains.value || null) : null,
        exclude_triggers_contains: el.exclTrigs ? (el.exclTrigs.value || null) : null,
        host_name_contains: el.hostContains ? (el.hostContains.value || null) : null,
        exclude_hosts_contains: el.exclHosts ? (el.exclHosts.value || null) : null,
        tags_include: el.tagsInclude ? (el.tagsInclude.value || null) : null,
        tags_exclude: el.tagsExclude ? (el.tagsExclude.value || null) : null,
        ack_filter: el.ackFilter ? (el.ackFilter.value || 'all') : 'all',
        x_axis_rotate_labels: el.xRotate ? !!el.xRotate.checked : true,
        x_axis_alternate_days: el.xAlternate ? !!el.xAlternate.checked : true,
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
            <div class="mb-3"><label class="form-label" for="incChHostContains">Filtrar Hosts (contendo)</label>
              <input type="text" class="form-control" id="incChHostContains" placeholder="ex: firewall">
            </div>
            <div class="mb-3"><label class="form-label" for="incChExcludeHosts">Excluir Hosts (contendo)</label>
              <input type="text" class="form-control" id="incChExcludeHosts" placeholder="ex: teste, lab">
            </div>
            <div class="mb-3"><label class="form-label" for="incChTriggerContains">Filtrar Triggers (contendo)</label>
              <input type="text" class="form-control" id="incChTriggerContains" placeholder="ex: link down">
            </div>
            <div class="mb-3"><label class="form-label" for="incChExcludeTriggers">Excluir Triggers (contendo)</label>
              <input type="text" class="form-control" id="incChExcludeTriggers" placeholder="ex: cpu, memoria">
            </div>
            <div class="mb-3"><label class="form-label" for="incChTagsInclude">Tags (incluir)</label>
              <input type="text" class="form-control" id="incChTagsInclude" placeholder="ex: service:web, env:prod">
            </div>
            <div class="mb-3"><label class="form-label" for="incChTagsExclude">Tags (excluir)</label>
              <input type="text" class="form-control" id="incChTagsExclude" placeholder="ex: env:dev">
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
            <div class="mb-3"><label class="form-label" for="incChProblemTypeTopN">Top N (Tipos de Problema) — 0 = Todos</label>
              <input type="number" class="form-control" id="incChProblemTypeTopN" min="0" placeholder="10"></div>
            <div class="mb-3"><label class="form-label" for="incChProblemTypeKey">Agrupar Top N por</label>
              <select class="form-select" id="incChProblemTypeKey">
                <option value="triggerid">Trigger (ID) — estável</option>
                <option value="name">Nome do Evento — volátil</option>
              </select>
            </div>
            <div class="mb-3"><label class="form-label" for="incChDailyType">Volume Diário: Estilo</label>
              <select class="form-select" id="incChDailyType"><option value="bar">Barras</option><option value="line">Linhas</option></select>
            </div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incChXRotate" checked><label class="form-check-label" for="incChXRotate">Rotacionar rótulos do eixo X</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incChXAlternate" checked><label class="form-check-label" for="incChXAlternate">Dias alternados no eixo X</label></div>
          </div>
            <div class="mb-3"><label class="form-label" for="incChTimeGranularity">Granularidade do Tempo</label>
              <select class="form-select" id="incChTimeGranularity"><option value="D">Dia</option><option value="W">Semana</option><option value="M">Mes</option></select>
            </div>
            <div class="mb-3"><label class="form-label" for="incChAckFilter">Filtro de ACK</label>
              <select class="form-select" id="incChAckFilter"><option value="all">Todos</option><option value="only_acked">Somente com ACK</option><option value="only_unacked">Somente sem ACK</option></select>
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
