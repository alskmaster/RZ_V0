(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['mem_chart'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureMemChartModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        host: document.getElementById('memChHostContains'),
        topN: document.getElementById('memChTopN'),
        colorMin: document.getElementById('memChColorMin'),
        colorAvg: document.getElementById('memChColorAvg'),
        colorMax: document.getElementById('memChColorMax'),
        saveBtn: document.getElementById('saveMemChBtn')
      };
    },
    load(o){
      this._ensure(); o = o||{}; const el = this.elements;
      el.host.value = o.host_name_contains || '';
      el.topN.value = o.top_n ?? 0;
      el.colorMin.value = o.color_min || '#0047b3';
      el.colorAvg.value = o.color_avg || '#3385ff';
      el.colorMax.value = o.color_max || '#66b3ff';
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      return {
        host_name_contains: el.host.value || null,
        top_n: el.topN.value ? parseInt(el.topN.value) : 0,
        color_min: el.colorMin.value,
        color_avg: el.colorAvg.value,
        color_max: el.colorMax.value,
      };
    }
  };

  function ensureMemChartModal(){
    let el = document.getElementById('customizeMemChModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeMemChModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Memória (Gráficos)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label" for="memChHostContains">Filtrar hosts (contém)</label>
            <input type="text" class="form-control" id="memChHostContains" placeholder="Parte do nome do host"/>
          </div>
          <div class="row g-3">
            <div class="col-4">
              <label class="form-label" for="memChTopN">Top N</label>
              <input type="number" class="form-control" id="memChTopN" min="0" value="0"/>
            </div>
            <div class="col-4">
              <label class="form-label" for="memChColorMax">Cor Máximo</label>
              <input type="color" class="form-control form-control-color" id="memChColorMax" value="#66b3ff"/>
            </div>
            <div class="col-4">
              <label class="form-label" for="memChColorAvg">Cor Médio</label>
              <input type="color" class="form-control form-control-color" id="memChColorAvg" value="#3385ff"/>
            </div>
            <div class="col-4">
              <label class="form-label" for="memChColorMin">Cor Mínimo</label>
              <input type="color" class="form-control form-control-color" id="memChColorMin" value="#0047b3"/>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveMemChBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeMemChModal');
  }
})();

