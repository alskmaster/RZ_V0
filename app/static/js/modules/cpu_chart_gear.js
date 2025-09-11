(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};
  window.ModuleCustomizers['cpu_chart'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureCpuCh();
      if(!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        // gerais
        title: document.getElementById('cpuChTitle'),
        periodSubFilter: document.getElementById('cpuChPeriodSubFilter'),
        showSummary: document.getElementById('cpuChShowSummary'),
        // filtros
        host: document.getElementById('cpuChHostContains'),
        excludeHosts: document.getElementById('cpuChExcludeHosts'),
        topN: document.getElementById('cpuChTopN'),
        // visual
        chartType: document.getElementById('cpuChChartType'),
        rotateX: document.getElementById('cpuChRotateX'),
        colorMax: document.getElementById('cpuChColorMax'),
        colorAvg: document.getElementById('cpuChColorAvg'),
        colorMin: document.getElementById('cpuChColorMin'),
        showValues: document.getElementById('cpuChShowValues'),
        labelWrap: document.getElementById('cpuChLabelWrap'),
        // ação
        saveBtn: document.getElementById('saveCpuChBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      if (el.showSummary) el.showSummary.checked = (o.show_summary !== false);
      // filtros
      el.host.value = o.host_name_contains || '';
      if (el.excludeHosts) el.excludeHosts.value = o.exclude_hosts_contains || '';
      el.topN.value = (o.top_n != null && o.top_n !== '') ? o.top_n : 5;
      // visual
      el.chartType.value = o.chart_type || 'bar';
      el.rotateX.checked = !!o.rotate_x_labels;
      el.colorMax.value = o.color_max || '#ff9999';
      el.colorAvg.value = o.color_avg || '#ff4d4d';
      el.colorMin.value = o.color_min || '#cc0000';
      el.showValues.checked = (o.show_values !== false);
      if (el.labelWrap) el.labelWrap.value = o.label_wrap || 48;
      // salvar
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      const tn = el.topN.value === '' ? 0 : (parseInt(el.topN.value, 10) || 0);
      return {
        __title: el.title.value || '',
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        show_summary: el.showSummary ? !!el.showSummary.checked : true,
        // filtros
        host_name_contains: el.host.value || null,
        exclude_hosts_contains: el.excludeHosts ? (el.excludeHosts.value || null) : null,
        top_n: tn,
        // visual
        chart_type: el.chartType.value || 'bar',
        rotate_x_labels: !!el.rotateX.checked,
        color_max: el.colorMax.value,
        color_avg: el.colorAvg.value,
        color_min: el.colorMin.value,
        show_values: !!el.showValues.checked,
        label_wrap: el.labelWrap && el.labelWrap.value ? parseInt(el.labelWrap.value, 10) : 48
      };
    }
  };

  function ensureCpuCh(){
    let el = document.getElementById('customizeCpuChModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
  <div class="modal fade" id="customizeCpuChModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg"><div class="modal-content">
      <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: CPU (Gráficos)</h5><button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button></div>
      <div class="modal-body">
        <div class="row g-3">
          <!-- Título -->
          <div class="col-12">
            <label class="form-label" for="cpuChTitle">Título do módulo</label>
            <input type="text" class="form-control" id="cpuChTitle" placeholder="Ex: CPU (Gráficos)"/>
          </div>
          <!-- Período -->
          <div class="col-md-4">
            <label class="form-label" for="cpuChPeriodSubFilter">Período</label>
            <select class="form-select" id="cpuChPeriodSubFilter">
              <option value="full_month">Mês Completo</option>
              <option value="last_7d">Últimos 7 dias</option>
              <option value="last_24h">Últimas 24h</option>
            </select>
          </div>
          <!-- Resumo explicativo -->
          <div class="col-md-4 form-check d-flex align-items-end">
            <div>
              <input class="form-check-input" type="checkbox" id="cpuChShowSummary" checked>
              <label class="form-check-label" for="cpuChShowSummary">Exibir resumo explicativo</label>
            </div>
          </div>
          <!-- Filtros de host -->
          <div class="col-md-6">
            <label class="form-label" for="cpuChHostContains">Filtrar hosts (contendo)</label>
            <input type="text" class="form-control" id="cpuChHostContains" placeholder="Parte do nome do host"/>
          </div>
          <div class="col-md-6">
            <label class="form-label" for="cpuChExcludeHosts">Excluir hosts (contendo)</label>
            <input type="text" class="form-control" id="cpuChExcludeHosts" placeholder="Lista separada por vírgula"/>
          </div>
          <!-- Top N -->
          <div class="col-md-3">
            <label class="form-label" for="cpuChTopN">Top N</label>
            <input type="number" class="form-control" id="cpuChTopN" min="0" placeholder="vazio = todos" value="5"/>
          </div>
          <!-- Tipo de gráfico -->
          <div class="col-md-3">
            <label class="form-label" for="cpuChChartType">Tipo de Gráfico</label>
            <select class="form-select" id="cpuChChartType">
              <option value="pie">Pizza</option>
              <option value="bar" selected>Barras</option>
            </select>
          </div>
          <!-- Rotacionar rótulos eixo X -->
          <div class="col-md-3 form-check d-flex align-items-end">
            <div>
              <input class="form-check-input" type="checkbox" id="cpuChRotateX">
              <label class="form-check-label" for="cpuChRotateX">Rotacionar rótulos do eixo X</label>
            </div>
          </div>
          <!-- Mostrar valores -->
          <div class="col-md-3 form-check d-flex align-items-end">
            <div>
              <input class="form-check-input" type="checkbox" id="cpuChShowValues" checked>
              <label class="form-check-label" for="cpuChShowValues">Mostrar valores no gráfico</label>
            </div>
          </div>
          <!-- Cores -->
          <div class="col-md-4">
            <label class="form-label" for="cpuChColorMax">Cor Máximo</label>
            <input type="color" class="form-control form-control-color" id="cpuChColorMax" value="#ff9999"/>
          </div>
          <div class="col-md-4">
            <label class="form-label" for="cpuChColorAvg">Cor Médio</label>
            <input type="color" class="form-control form-control-color" id="cpuChColorAvg" value="#ff4d4d"/>
          </div>
          <div class="col-md-4">
            <label class="form-label" for="cpuChColorMin">Cor Mínimo</label>
            <input type="color" class="form-control form-control-color" id="cpuChColorMin" value="#cc0000"/>
          </div>
          <!-- Tamanho máx. do rótulo -->
          <div class="col-md-4">
            <label class="form-label" for="cpuChLabelWrap">Tamanho máx. do rótulo</label>
            <input type="number" class="form-control" id="cpuChLabelWrap" min="10" value="48"/>
          </div>
        </div>
      </div>
      <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button><button type="button" class="btn btn-primary" id="saveCpuChBtn">Salvar</button></div>
    </div></div>
  </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeCpuChModal');
  }
})();

