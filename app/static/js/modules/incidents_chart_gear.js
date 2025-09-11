(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['incidents_chart'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureIncidentsChartModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: el.querySelector('#incChTitle'),
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
        hostContains: el.querySelector('#incChHostContains'),
        exclHosts: el.querySelector('#incChExcludeHosts'),
        trigContains: el.querySelector('#incChTriggerContains'),
        exclTrigs: el.querySelector('#incChExcludeTriggers'),
        tagsInclude: el.querySelector('#incChTagsInclude'),
        tagsExclude: el.querySelector('#incChTagsExclude'),
        xRotate: el.querySelector('#incChXRotate'),
        xAlternate: el.querySelector('#incChXAlternate'),
        timeGran: el.querySelector('#incChTimeGranularity'),
        ackFilter: el.querySelector('#incChAckFilter'),
        saveBtn: el.querySelector('#saveIncChCustomizationBtn')
      };
    },
    load(opts){
      this._ensure();
      const o = opts || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      const def = ['info','warning','average','high','disaster'];
      const sel = o.severities || def;
      el.severityInfo.checked = sel.includes('info');
      el.severityWarning.checked = sel.includes('warning');
      el.severityAverage.checked = sel.includes('average');
      el.severityHigh.checked = sel.includes('high');
      el.severityDisaster.checked = sel.includes('disaster');
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.chartType.value = o.chart_type || 'severity_pie';
      el.problemTypeTopN.value = (o.problem_type_top_n != null ? o.problem_type_top_n : '');
      el.problemTypeKey.value = o.problem_type_key || 'triggerid';
      el.dailyType.value = o.daily_volume_chart_type || 'bar';
      el.hostContains.value = o.host_name_contains || '';
      el.exclHosts.value = o.exclude_hosts_contains || '';
      el.trigContains.value = o.trigger_name_contains || '';
      el.exclTrigs.value = o.exclude_triggers_contains || '';
      el.tagsInclude.value = o.tags_include || '';
      el.tagsExclude.value = o.tags_exclude || '';
      el.xRotate.checked = o.x_axis_rotate_labels !== false;
      el.xAlternate.checked = o.x_axis_alternate_days !== false;
      el.timeGran.value = o.time_granularity || 'D';
      el.ackFilter.value = o.ack_filter || 'all';
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements; const severities = [];
      if (el.severityInfo.checked) severities.push('info');
      if (el.severityWarning.checked) severities.push('warning');
      if (el.severityAverage.checked) severities.push('average');
      if (el.severityHigh.checked) severities.push('high');
      if (el.severityDisaster.checked) severities.push('disaster');
      const dailySev = severities.slice();
      return {
        __title: el.title.value || '',
        severities,
        period_sub_filter: el.periodSubFilter.value,
        chart_type: el.chartType.value,
        problem_type_top_n: el.problemTypeTopN.value ? parseInt(el.problemTypeTopN.value) : null,
        problem_type_key: el.problemTypeKey.value,
        daily_volume_chart_type: el.dailyType.value,
        daily_volume_severities: dailySev,
        time_granularity: el.timeGran.value,
        trigger_name_contains: el.trigContains.value || null,
        exclude_triggers_contains: el.exclTrigs.value || null,
        host_name_contains: el.hostContains.value || null,
        exclude_hosts_contains: el.exclHosts.value || null,
        tags_include: el.tagsInclude.value || null,
        tags_exclude: el.tagsExclude.value || null,
        ack_filter: el.ackFilter.value || 'all',
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
          <div class="col-12">
            <div class="mb-3"><label class="form-label" for="incChTitle">Título do módulo</label>
              <input type="text" class="form-control" id="incChTitle" placeholder="Ex: Incidentes (Gráficos)"/>
            </div>
          </div>
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
                <option value="last_7d">Últimos 7 dias</option>
                <option value="last_24h">Últimas 24h</option>
              </select>
            </div>
            <div class="mb-3"><label class="form-label" for="incChHostContains">Filtrar Hosts (contendo)</label>
              <input type="text" class="form-control" id="incChHostContains" placeholder="ex: firewall">
            </div>
            <div class="mb-3"><label class="form-label" for="incChExcludeHosts">Excluir Hosts (contendo)</label>
              <input type="text" class="form-control" id="incChExcludeHosts" placeholder="ex: teste, lab">
            </div>
            <div class="mb-3"><label class="form-label" for="incChTriggerContains">Filtrar problema (contendo)</label>
              <input type="text" class="form-control" id="incChTriggerContains" placeholder="ex: link down">
            </div>
            <div class="mb-3"><label class="form-label" for="incChExcludeTriggers">Excluir problema (contendo)</label>
              <input type="text" class="form-control" id="incChExcludeTriggers" placeholder="Palavras separadas por vírgula">
            </div>
            <div class="mb-3"><label class="form-label" for="incChTagsInclude">Filtrar tags (contendo)</label>
              <input type="text" class="form-control" id="incChTagsInclude" placeholder="ex: service:web, env:prod">
            </div>
            <div class="mb-3"><label class="form-label" for="incChTagsExclude">Excluir tags (contendo)</label>
              <input type="text" class="form-control" id="incChTagsExclude" placeholder="ex: env:dev">
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
          <div class="col-12">
            <div class="mb-3"><label class="form-label" for="incChTimeGranularity">Granularidade do Tempo</label>
              <select class="form-select" id="incChTimeGranularity"><option value="D">Dia</option><option value="W">Semana</option><option value="M">Mês</option></select>
            </div>
            <div class="mb-3"><label class="form-label" for="incChAckFilter">Filtro de ACK</label>
              <select class="form-select" id="incChAckFilter"><option value="all">Todos</option><option value="only_acked">Somente com ACK</option><option value="only_unacked">Somente sem ACK</option></select>
            </div>
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

