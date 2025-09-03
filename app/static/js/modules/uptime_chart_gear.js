(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['uptime_chart'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureUptimeChartModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        topN: document.getElementById('uptChTopN'),
        order: document.getElementById('uptChOrder'),
        color: document.getElementById('uptChColor'),
        target: document.getElementById('uptChTarget'),
        below: document.getElementById('uptChBelowColor'),
        labelWrap: document.getElementById('uptChLabelWrap'),
        dyn: document.getElementById('uptChDyn'),
        hpb: document.getElementById('uptChHPB'),
        showValues: document.getElementById('uptChShowValues'),
        grid: document.getElementById('uptChGrid'),
        saveBtn: document.getElementById('saveUptChBtn')
      };
    },
    load(o){
      this._ensure(); o = o||{}; const el = this.elements;
      el.topN.value = o.top_n ?? 0;
      el.order.value = o.order || 'desc';
      el.color.value = o.color || '#4e79a7';
      el.target.value = o.target_days ?? '';
      el.below.value = o.below_color || '#e55353';
      el.labelWrap.value = o.label_wrap ?? 45;
      el.dyn.checked = o.dynamic_height !== false;
      el.hpb.value = o.height_per_bar ?? 0.35;
      el.showValues.checked = o.show_values !== false;
      el.grid.checked = o.grid !== false;
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      return {
        top_n: el.topN.value ? parseInt(el.topN.value) : 0,
        order: el.order.value,
        color: el.color.value || '#4e79a7',
        target_days: el.target.value ? parseFloat(el.target.value) : null,
        below_color: el.below.value || '#e55353',
        label_wrap: el.labelWrap.value ? parseInt(el.labelWrap.value) : 45,
        dynamic_height: !!el.dyn.checked,
        height_per_bar: el.hpb.value ? parseFloat(el.hpb.value) : 0.35,
        show_values: !!el.showValues.checked,
        grid: !!el.grid.checked,
      };
    }
  };

  function ensureUptimeChartModal(){
    let el = document.getElementById('customizeUptimeChartModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeUptimeChartModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Uptime (Gráficos)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-4">
              <label class="form-label" for="uptChTopN">Top N</label>
              <input type="number" id="uptChTopN" class="form-control" min="0" value="0"/>
            </div>
            <div class="col-4">
              <label class="form-label" for="uptChOrder">Ordem</label>
              <select id="uptChOrder" class="form-select">
                <option value="desc">Maior → Menor</option>
                <option value="asc">Menor → Maior</option>
              </select>
            </div>
            <div class="col-4">
              <label class="form-label" for="uptChLabelWrap">Quebra de rótulo</label>
              <input type="number" id="uptChLabelWrap" class="form-control" value="45" min="10" max="90"/>
            </div>
            <div class="col-6">
              <label class="form-label" for="uptChColor">Cor</label>
              <input type="color" id="uptChColor" class="form-control form-control-color" value="#4e79a7"/>
            </div>
            <div class="col-6">
              <label class="form-label" for="uptChBelowColor">Cor (abaixo da meta)</label>
              <input type="color" id="uptChBelowColor" class="form-control form-control-color" value="#e55353"/>
            </div>
            <div class="col-6">
              <label class="form-label" for="uptChTarget">Meta de dias</label>
              <input type="number" id="uptChTarget" class="form-control" step="0.5"/>
            </div>
            <div class="col-6">
              <label class="form-label" for="uptChHPB">Altura por barra</label>
              <input type="number" id="uptChHPB" class="form-control" step="0.05" value="0.35"/>
            </div>
            <div class="col-6 form-check">
              <input class="form-check-input" type="checkbox" id="uptChDyn" checked>
              <label class="form-check-label" for="uptChDyn">Altura dinâmica</label>
            </div>
            <div class="col-6 form-check">
              <input class="form-check-input" type="checkbox" id="uptChShowValues" checked>
              <label class="form-check-label" for="uptChShowValues">Mostrar valores</label>
            </div>
            <div class="col-6 form-check">
              <input class="form-check-input" type="checkbox" id="uptChGrid" checked>
              <label class="form-check-label" for="uptChGrid">Grade</label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveUptChBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeUptimeChartModal');
  }
})();
