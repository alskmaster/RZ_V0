(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers["latency_chart"] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureLatChModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        // gerais
        title: document.getElementById("latChTitle"),
        periodSubFilter: document.getElementById("latChPeriodSubFilter"),
        showSummary: document.getElementById("latChShowSummary"),
        // filtros
        host: document.getElementById("latChHostContains"),
        excludeHosts: document.getElementById("latChExcludeHosts"),
        topN: document.getElementById("latChTopN"),
        // visual
        chartType: document.getElementById("latChChartType"),
        rotateX: document.getElementById("latChRotateX"),
        colorMax: document.getElementById("latChColorMax"),
        colorAvg: document.getElementById("latChColorAvg"),
        colorMin: document.getElementById("latChColorMin"),
        showValues: document.getElementById("latChShowValues"),
        labelWrap: document.getElementById("latChLabelWrap"),
        // ação
        saveBtn: document.getElementById("saveLatChBtn")
      };
    },
    load(o){
      this._ensure(); o = o||{}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ""; } catch(e) {}
      el.periodSubFilter.value = o.period_sub_filter || "full_month";
      if (el.showSummary) el.showSummary.checked = (o.show_summary !== false);
      // filtros
      el.host.value = o.host_name_contains || "";
      if (el.excludeHosts) el.excludeHosts.value = o.exclude_hosts_contains || "";
      el.topN.value = (o.top_n != null && o.top_n !== "") ? o.top_n : 5;
      // visual
      el.chartType.value = o.chart_type || "bar";
      el.rotateX.checked = !!o.rotate_x_labels;
      el.colorMax.value = o.color_max || "#ffb3b3";
      el.colorAvg.value = o.color_avg || "#ff6666";
      el.colorMin.value = o.color_min || "#cc0000";
      el.showValues.checked = (o.show_values !== false);
      if (el.labelWrap) el.labelWrap.value = o.label_wrap || 48;
      // salvar
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener("click", ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      const tn = el.topN.value === "" ? 0 : (parseInt(el.topN.value, 10) || 0);
      return {
        __title: el.title.value || "",
        period_sub_filter: el.periodSubFilter.value || "full_month",
        show_summary: el.showSummary ? !!el.showSummary.checked : true,
        host_name_contains: el.host.value || null,
        exclude_hosts_contains: el.excludeHosts ? (el.excludeHosts.value || null) : null,
        top_n: tn,
        chart_type: el.chartType.value || "bar",
        rotate_x_labels: !!el.rotateX.checked,
        color_max: el.colorMax.value,
        color_avg: el.colorAvg.value,
        color_min: el.colorMin.value,
        show_values: !!el.showValues.checked,
        label_wrap: el.labelWrap && el.labelWrap.value ? parseInt(el.labelWrap.value, 10) : 48
      };
    }
  };

  function ensureLatChModal(){
    let el = document.getElementById("customizeLatChModal");
    if (el) return el;
    const tpl = document.createElement("div");
    tpl.innerHTML = `
    <div class="modal fade" id="customizeLatChModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Latência (Gráficos)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <!-- Título -->
            <div class="col-12">
              <label class="form-label" for="latChTitle">Título do módulo</label>
              <input type="text" class="form-control" id="latChTitle" placeholder="Ex: Latência (Gráficos)"/>
            </div>
            <!-- Período + resumo -->
            <div class="col-md-4">
              <label class="form-label" for="latChPeriodSubFilter">Período</label>
              <select class="form-select" id="latChPeriodSubFilter">
                <option value="full_month">Mês Completo</option>
                <option value="last_7d">Últimos 7 dias</option>
                <option value="last_24h">Últimas 24h</option>
              </select>
            </div>
            <div class="col-md-4 form-check d-flex align-items-end">
              <div>
                <input class="form-check-input" type="checkbox" id="latChShowSummary" checked>
                <label class="form-check-label" for="latChShowSummary">Exibir resumo explicativo</label>
              </div>
            </div>
            <!-- Filtros por host -->
            <div class="col-md-6">
              <label class="form-label" for="latChHostContains">Filtrar hosts (contendo)</label>
              <input type="text" class="form-control" id="latChHostContains" placeholder="Parte do nome do host"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="latChExcludeHosts">Excluir hosts (contendo)</label>
              <input type="text" class="form-control" id="latChExcludeHosts" placeholder="Lista separada por vírgula"/>
            </div>
            <!-- Top N / tipo gráfico / opções visuais -->
            <div class="col-md-3">
              <label class="form-label" for="latChTopN">Top N</label>
              <input type="number" class="form-control" id="latChTopN" min="0" placeholder="vazio = todos" value="5"/>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="latChChartType">Tipo de Gráfico</label>
              <select class="form-select" id="latChChartType">
                <option value="pie">Pizza</option>
                <option value="bar" selected>Barras</option>
              </select>
            </div>
            <div class="col-md-3 form-check d-flex align-items-end">
              <div>
                <input class="form-check-input" type="checkbox" id="latChRotateX">
                <label class="form-check-label" for="latChRotateX">Rotacionar rótulos do eixo X</label>
              </div>
            </div>
            <div class="col-md-3 form-check d-flex align-items-end">
              <div>
                <input class="form-check-input" type="checkbox" id="latChShowValues" checked>
                <label class="form-check-label" for="latChShowValues">Mostrar valores no gráfico</label>
              </div>
            </div>
            <!-- Cores -->
            <div class="col-md-4">
              <label class="form-label" for="latChColorMax">Cor Máximo</label>
              <input type="color" class="form-control form-control-color" id="latChColorMax" value="#ffb3b3"/>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="latChColorAvg">Cor Médio</label>
              <input type="color" class="form-control form-control-color" id="latChColorAvg" value="#ff6666"/>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="latChColorMin">Cor Mínimo</label>
              <input type="color" class="form-control form-control-color" id="latChColorMin" value="#cc0000"/>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="latChLabelWrap">Tamanho máx. do rótulo</label>
              <input type="number" class="form-control" id="latChLabelWrap" min="10" value="48"/>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveLatChBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById("customizeLatChModal");
  }
})();