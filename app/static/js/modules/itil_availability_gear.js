(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['itil_availability'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureITILAvailabilityModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('iaTitle'),
        itemid: document.getElementById('iaItemId'),
        valueType: document.getElementById('iaValueType'),
        sevInfo: document.getElementById('iaSevInfo'),
        sevWarn: document.getElementById('iaSevWarn'),
        sevAvg: document.getElementById('iaSevAvg'),
        sevHigh: document.getElementById('iaSevHigh'),
        sevDis: document.getElementById('iaSevDis'),
        saveBtn: document.getElementById('saveIABtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.itemid.value = (o.itemid != null ? String(o.itemid) : '');
      el.valueType.value = String(o.value_type != null ? o.value_type : 0);
      const sel = new Set(o.severities || ['info','warning','average','high','disaster']);
      el.sevInfo.checked = sel.has('info');
      el.sevWarn.checked = sel.has('warning');
      el.sevAvg.checked = sel.has('average');
      el.sevHigh.checked = sel.has('high');
      el.sevDis.checked = sel.has('disaster');
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements; const severities = [];
      if (el.sevInfo.checked) severities.push('info');
      if (el.sevWarn.checked) severities.push('warning');
      if (el.sevAvg.checked) severities.push('average');
      if (el.sevHigh.checked) severities.push('high');
      if (el.sevDis.checked) severities.push('disaster');
      return {
        __title: el.title.value || '',
        itemid: el.itemid.value ? el.itemid.value.trim() : null,
        value_type: parseInt(el.valueType.value || '0', 10),
        severities: severities.length ? severities : ['info','warning','average','high','disaster']
      };
    }
  };

  function ensureITILAvailabilityModal(){
    let el = document.getElementById('customizeITILAvailabilityModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeITILAvailabilityModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Disponibilidade por Incidente (ITIL)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="iaTitle">Título do módulo</label>
              <input type="text" class="form-control" id="iaTitle" placeholder="Ex: Disponibilidade por Incidente"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="iaItemId">ItemID</label>
              <input type="text" class="form-control" id="iaItemId" placeholder="12345"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="iaValueType">Tipo de histórico</label>
              <select class="form-select" id="iaValueType">
                <option value="0">Numeric float (0)</option>
                <option value="1">Character (1)</option>
                <option value="2">Log (2)</option>
                <option value="3">Numeric unsigned (3)</option>
              </select>
            </div>
            <div class="col-12">
              <label class="form-label">Severidades</label>
              <div class="d-flex gap-3 flex-wrap">
                <div class="form-check"><input class="form-check-input" type="checkbox" id="iaSevInfo" checked> <label class="form-check-label" for="iaSevInfo">Informação</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="iaSevWarn" checked> <label class="form-check-label" for="iaSevWarn">Atenção</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="iaSevAvg" checked> <label class="form-check-label" for="iaSevAvg">Média</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="iaSevHigh" checked> <label class="form-check-label" for="iaSevHigh">Alta</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="iaSevDis" checked> <label class="form-check-label" for="iaSevDis">Desastre</label></div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveIABtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeITILAvailabilityModal');
  }
})();

