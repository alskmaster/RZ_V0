(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['resilience_services'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureResilienceServicesModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        titleInput: document.getElementById('resSvcTitle'),
        serviceIds: document.getElementById('resSvcIds'),
        svcNameContains: document.getElementById('resSvcNameContains'),
        tagsText: document.getElementById('resSvcTags'),
        decimals: document.getElementById('resSvcDecimals'),
        highlight: document.getElementById('resSvcHighlight'),
        orderBy: document.getElementById('resSvcOrderBy'),
        orderAsc: document.getElementById('resSvcOrderAsc'),
        topN: document.getElementById('resSvcTopN'),
        showTrend: document.getElementById('resSvcShowTrend'),
        trendGran: document.getElementById('resSvcTrendGran'),
        chartColor: document.getElementById('resSvcChartColor'),
        belowColor: document.getElementById('resSvcBelowColor'),
        xAxis0100: document.getElementById('resSvcXAxis0100'),
        saveBtn: document.getElementById('saveResilienceServicesBtn')
      };
    },
    load(o){
      this._ensure();
      o = o || {}; const el = this.elements;
      try {
        const curr = window.currentModuleToCustomize || null;
        el.titleInput.value = (curr && curr.title) ? String(curr.title) : '';
      } catch(e) { el.titleInput.value = ''; }
      el.serviceIds.value = (Array.isArray(o.serviceids) ? o.serviceids.join(',') : (o.serviceids || ''));
      el.svcNameContains.value = o.service_name_contains || '';
      // tags in format tag=value;tag2=value2
      try {
        if (Array.isArray(o.tags)) {
          el.tagsText.value = o.tags.map(t => `${t.tag||''}=${t.value||''}`).join(';');
        } else {
          el.tagsText.value = '';
        }
      } catch(e) { el.tagsText.value = ''; }
      el.decimals.value = (o.decimals ?? 2);
      el.highlight.checked = (o.highlight_below_goal !== false);
      el.orderBy.value = o.sort_by || 'sla';
      el.orderAsc.checked = (o.sort_asc !== false);
      el.topN.value = o.top_n || '';
      el.showTrend.checked = !!o.show_trend;
      el.trendGran.value = (o.trend_granularity || 'D');
      el.chartColor.value = o.chart_color || '#4e79a7';
      el.belowColor.value = o.below_color || '#e15759';
      el.xAxis0100.checked = !!o.x_axis_0_100;
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      // parse tags
      const tags = [];
      const txt = (el.tagsText.value || '').trim();
      if (txt) {
        txt.split(';').forEach(pair => {
          const [k,v] = pair.split('=');
          if ((k||'').trim()) tags.push({ tag: (k||'').trim(), value: (v||'').trim() });
        });
      }
      const idsCSV = (el.serviceIds.value || '').trim();
      const ids = idsCSV ? idsCSV.split(',').map(s => s.trim()).filter(Boolean) : null;
      return {
        __title: el.titleInput.value || '',
        serviceids: ids,
        service_name_contains: el.svcNameContains.value || null,
        tags: tags,
        decimals: el.decimals.value ? parseInt(el.decimals.value, 10) : 2,
        highlight_below_goal: !!el.highlight.checked,
        sort_by: el.orderBy.value || 'sla',
        sort_asc: !!el.orderAsc.checked,
        top_n: el.topN.value ? parseInt(el.topN.value, 10) : null,
        show_trend: !!el.showTrend.checked,
        trend_granularity: el.trendGran.value || 'D',
        chart_color: el.chartColor.value || '#4e79a7',
        below_color: el.belowColor.value || '#e15759',
        x_axis_0_100: !!el.xAxis0100.checked,
      };
    }
  };

  function ensureResilienceServicesModal(){
    let el = document.getElementById('customizeResilienceServicesModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeResilienceServicesModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Personalizar Módulo: SLA de Serviços (Preciso)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="resSvcTitle">Título do módulo</label>
              <input type="text" class="form-control" id="resSvcTitle" placeholder="Ex: SLA de Serviços"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="resSvcIds">IDs de serviços (CSV)</label>
              <input type="text" class="form-control" id="resSvcIds" placeholder="Ex: 12,34,56"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="resSvcNameContains">Nome do serviço (contém)</label>
              <input type="text" class="form-control" id="resSvcNameContains" placeholder="Parte do nome"/>
            </div>
            <div class="col-md-12">
              <label class="form-label" for="resSvcTags">Tags (formato tag=valor;tag2=valor2)</label>
              <input type="text" class="form-control" id="resSvcTags" placeholder="Ex: area=network;tipo=core"/>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="resSvcDecimals">Casas decimais (SLA %)</label>
              <input type="number" class="form-control" id="resSvcDecimals" min="0" max="6" value="2"/>
            </div>
            <div class="col-md-3 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resSvcHighlight" checked>
              <label class="form-check-label" for="resSvcHighlight">Destacar abaixo da meta</label>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="resSvcOrderBy">Ordenar por</label>
              <select class="form-select" id="resSvcOrderBy">
                <option value="sla">SLA (%)</option>
                <option value="downtime">Downtime (s)</option>
                <option value="service">Serviço</option>
              </select>
            </div>
            <div class="col-md-3 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resSvcOrderAsc" checked>
              <label class="form-check-label" for="resSvcOrderAsc">Ascendente</label>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="resSvcTopN">Top N</label>
              <input type="number" class="form-control" id="resSvcTopN" min="1" placeholder="Opcional"/>
            </div>
            <div class="col-md-3 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resSvcShowTrend">
              <label class="form-check-label" for="resSvcShowTrend">Exibir tendência</label>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="resSvcTrendGran">Granularidade</label>
              <select class="form-select" id="resSvcTrendGran">
                <option value="D">Diária</option>
                <option value="W">Semanal</option>
              </select>
            </div>
            <div class="col-md-3 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resSvcXAxis0100">
              <label class="form-check-label" for="resSvcXAxis0100">Eixo X 0..100</label>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="resSvcChartColor">Cor das barras</label>
              <input type="color" class="form-control form-control-color" id="resSvcChartColor" value="#4e79a7"/>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="resSvcBelowColor">Cor abaixo da meta</label>
              <input type="color" class="form-control form-control-color" id="resSvcBelowColor" value="#e15759"/>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveResilienceServicesBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeResilienceServicesModal');
  }
})();

