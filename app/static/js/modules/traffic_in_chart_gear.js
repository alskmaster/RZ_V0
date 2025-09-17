(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers["traffic_in_chart"] = {
    modal: null,
    elements: {},
    _ensure(){
      const modalElement = ensureTrafficInChartModal();
      if (!this.modal) {
        this.modal = new bootstrap.Modal(modalElement);
      }
      this.elements = {
        title: document.getElementById('trafInChTitle'),
        periodSubFilter: document.getElementById('trafInChPeriodSubFilter'),
        showSummary: document.getElementById('trafInChShowSummary'),
        host: document.getElementById('trafInChHostContains'),
        excludeHosts: document.getElementById('trafInChExcludeHosts'),
        topN: document.getElementById('trafInChTopN'),
        chartType: document.getElementById('trafInChChartType'),
        rotateX: document.getElementById('trafInChRotateX'),
        colorMax: document.getElementById('trafInChColorMax'),
        colorAvg: document.getElementById('trafInChColorAvg'),
        colorMin: document.getElementById('trafInChColorMin'),
        showValues: document.getElementById('trafInChShowValues'),
        labelWrap: document.getElementById('trafInChLabelWrap'),
        saveBtn: document.getElementById('trafInChSaveBtn')
      };
    },
    load(options){
      this._ensure();
      const el = this.elements;
      const opts = options || {};
      try {
        el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || '';
      } catch (err) {
        el.title.value = '';
      }
      el.periodSubFilter.value = opts.period_sub_filter || 'full_month';
      if (el.showSummary) {
        el.showSummary.checked = opts.show_summary !== false;
      }
      el.host.value = opts.host_name_contains || '';
      if (el.excludeHosts) {
        el.excludeHosts.value = opts.exclude_hosts_contains || '';
      }
      const topValue = opts.top_n === 0 ? '' : (opts.top_n != null ? opts.top_n : 5);
      el.topN.value = topValue;
      el.chartType.value = (opts.chart_type || 'bar');
      el.rotateX.checked = !!opts.rotate_x_labels;
      el.colorMax.value = opts.color_max || '#ffc266';
      el.colorAvg.value = opts.color_avg || '#ffa31a';
      el.colorMin.value = opts.color_min || '#e68a00';
      el.showValues.checked = (opts.show_values !== false);
      el.labelWrap.value = opts.label_wrap || 48;

      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', () => {
        if (this._onSave) {
          this._onSave(this.save());
        }
        this.modal.hide();
      }, { once: true });
    },
    save(){
      const el = this.elements;
      const rawTop = (el.topN.value || '').trim();
      const topN = rawTop === '' ? 0 : (parseInt(rawTop, 10) || 0);
      const rawLabelWrap = (el.labelWrap && el.labelWrap.value) ? parseInt(el.labelWrap.value, 10) : 48;
      return {
        __title: el.title.value || '',
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        show_summary: el.showSummary ? !!el.showSummary.checked : true,
        host_name_contains: el.host.value || null,
        exclude_hosts_contains: el.excludeHosts ? (el.excludeHosts.value || null) : null,
        top_n: topN,
        chart_type: el.chartType.value || 'bar',
        rotate_x_labels: !!el.rotateX.checked,
        color_max: el.colorMax.value,
        color_avg: el.colorAvg.value,
        color_min: el.colorMin.value,
        show_values: !!el.showValues.checked,
        label_wrap: Number.isFinite(rawLabelWrap) && rawLabelWrap > 0 ? rawLabelWrap : 48
      };
    }
  };

  function ensureTrafficInChartModal(){
    let modal = document.getElementById('customizeTrafficInChartModal');
    if (modal) {
      return modal;
    }
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
    <div class="modal fade" id="customizeTrafficInChartModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Modulo: Trafego de Entrada (Graficos)</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label" for="trafInChTitle">Titulo do modulo</label>
                <input type="text" class="form-control" id="trafInChTitle" placeholder="Ex: Trafego de Entrada (Graficos)" />
              </div>
              <div class="col-md-4">
                <label class="form-label" for="trafInChPeriodSubFilter">Periodo</label>
                <select class="form-select" id="trafInChPeriodSubFilter">
                  <option value="full_month">Mes Completo</option>
                  <option value="last_7d">Ultimos 7 dias</option>
                  <option value="last_24h">Ultimas 24h</option>
                </select>
              </div>
              <div class="col-md-4 form-check d-flex align-items-end">
                <div>
                  <input class="form-check-input" type="checkbox" id="trafInChShowSummary" checked>
                  <label class="form-check-label" for="trafInChShowSummary">Exibir resumo explicativo</label>
                </div>
              </div>
              <div class="col-md-6">
                <label class="form-label" for="trafInChHostContains">Filtrar hosts (contendo)</label>
                <input type="text" class="form-control" id="trafInChHostContains" placeholder="Parte do nome do host" />
              </div>
              <div class="col-md-6">
                <label class="form-label" for="trafInChExcludeHosts">Excluir hosts (contendo)</label>
                <input type="text" class="form-control" id="trafInChExcludeHosts" placeholder="Lista separada por virgula" />
              </div>
              <div class="col-md-3">
                <label class="form-label" for="trafInChTopN">Top N</label>
                <input type="number" class="form-control" id="trafInChTopN" min="0" placeholder="vazio = todos" value="5" />
              </div>
              <div class="col-md-3">
                <label class="form-label" for="trafInChChartType">Tipo de Grafico</label>
                <select class="form-select" id="trafInChChartType">
                  <option value="bar">Barras</option>
                  <option value="line">Linha</option>
                  <option value="pie">Pizza</option>
                </select>
              </div>
              <div class="col-md-3 form-check d-flex align-items-end">
                <div>
                  <input class="form-check-input" type="checkbox" id="trafInChRotateX">
                  <label class="form-check-label" for="trafInChRotateX">Rotacionar rotulos do eixo X</label>
                </div>
              </div>
              <div class="col-md-3 form-check d-flex align-items-end">
                <div>
                  <input class="form-check-input" type="checkbox" id="trafInChShowValues" checked>
                  <label class="form-check-label" for="trafInChShowValues">Mostrar valores no grafico</label>
                </div>
              </div>
              <div class="col-md-4">
                <label class="form-label" for="trafInChColorMax">Cor Maximo</label>
                <input type="color" class="form-control form-control-color" id="trafInChColorMax" value="#ffc266" />
              </div>
              <div class="col-md-4">
                <label class="form-label" for="trafInChColorAvg">Cor Medio</label>
                <input type="color" class="form-control form-control-color" id="trafInChColorAvg" value="#ffa31a" />
              </div>
              <div class="col-md-4">
                <label class="form-label" for="trafInChColorMin">Cor Minimo</label>
                <input type="color" class="form-control form-control-color" id="trafInChColorMin" value="#e68a00" />
              </div>
              <div class="col-md-4">
                <label class="form-label" for="trafInChLabelWrap">Tamanho maximo do rotulo</label>
                <input type="number" class="form-control" id="trafInChLabelWrap" min="10" value="48" />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="trafInChSaveBtn">Salvar</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(wrapper.firstElementChild);
    return document.getElementById('customizeTrafficInChartModal');
  }
})();
