(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['mttr'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureMTTRModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('mttrTitle'),
        hostContains: document.getElementById('mttrHostContains'),
        periodSubFilter: document.getElementById('mttrPeriodSubFilter'),
        onlyAck: document.getElementById('mttrOnlyAck'),
        sevInfo: document.getElementById('mttrSevInfo'),
        sevWarn: document.getElementById('mttrSevWarn'),
        sevAvg: document.getElementById('mttrSevAvg'),
        sevHigh: document.getElementById('mttrSevHigh'),
        sevDis: document.getElementById('mttrSevDis'),
        saveBtn: document.getElementById('saveMTTRBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.hostContains.value = o.host_name_contains || '';
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.onlyAck.checked = !!o.only_acknowledged;
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
        host_name_contains: el.hostContains.value || null,
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        only_acknowledged: !!el.onlyAck.checked,
        severities: severities.length ? severities : ['info','warning','average','high','disaster']
      };
    }
  };

  function ensureMTTRModal(){
    let el = document.getElementById('customizeMTTRModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeMTTRModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: MTTR / MTTD</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="mttrTitle">Título do módulo</label>
              <input type="text" class="form-control" id="mttrTitle" placeholder="Ex: Eficiência da Resposta (MTTR)"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="mttrHostContains">Host (contém)</label>
              <input type="text" class="form-control" id="mttrHostContains" placeholder="Parte do nome do host"/>
            </div>
            <div class="col-md-3">
              <label class="form-label" for="mttrPeriodSubFilter">Período (sub-filtro)</label>
              <select class="form-select" id="mttrPeriodSubFilter">
                <option value="full_month">Mês completo</option>
                <option value="last_24h">Últimas 24h</option>
                <option value="last_7d">Últimos 7 dias</option>
              </select>
            </div>
            <div class="col-md-3 form-check d-flex align-items-end">
              <input class="form-check-input" type="checkbox" id="mttrOnlyAck"/>
              <label class="form-check-label ms-2" for="mttrOnlyAck">Somente reconhecidos</label>
            </div>
            <div class="col-12">
              <label class="form-label">Severidades</label>
              <div class="d-flex gap-3 flex-wrap">
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevInfo" checked> <label class="form-check-label" for="mttrSevInfo">Informação</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevWarn" checked> <label class="form-check-label" for="mttrSevWarn">Atenção</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevAvg" checked> <label class="form-check-label" for="mttrSevAvg">Média</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevHigh" checked> <label class="form-check-label" for="mttrSevHigh">Alta</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="mttrSevDis" checked> <label class="form-check-label" for="mttrSevDis">Desastre</label></div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveMTTRBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeMTTRModal');
  }
})();

