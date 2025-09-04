(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['unavailability_heatmap'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureUhmModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('uhmTitle'),
        hostContains: document.getElementById('uhmHostContains'),
        periodSubFilter: document.getElementById('uhmPeriodSubFilter'),
        palette: document.getElementById('uhmPalette'),
        annotate: document.getElementById('uhmAnnotate'),
        sevInfo: document.getElementById('uhmSevInfo'),
        sevWarn: document.getElementById('uhmSevWarn'),
        sevAvg: document.getElementById('uhmSevAvg'),
        sevHigh: document.getElementById('uhmSevHigh'),
        sevDis: document.getElementById('uhmSevDis'),
        saveBtn: document.getElementById('saveUhmBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.hostContains.value = o.host_name_contains || '';
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.palette.value = o.palette || 'OrRd';
      el.annotate.checked = (o.annotate !== false);
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
      const el = this.elements;
      const severities = [];
      if (el.sevInfo.checked) severities.push('info');
      if (el.sevWarn.checked) severities.push('warning');
      if (el.sevAvg.checked) severities.push('average');
      if (el.sevHigh.checked) severities.push('high');
      if (el.sevDis.checked) severities.push('disaster');
      return {
        __title: el.title.value || '',
        host_name_contains: el.hostContains.value || null,
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        palette: el.palette.value || 'OrRd',
        annotate: !!el.annotate.checked,
        severities: severities.length ? severities : ['info','warning','average','high','disaster']
      };
    }
  };

  function ensureUhmModal(){
    let el = document.getElementById('customizeUhmModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeUhmModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Personalizar Módulo: Mapa de Calor de Indisponibilidade</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="uhmTitle">Título do módulo</label>
              <input type="text" class="form-control" id="uhmTitle" placeholder="Ex: Mapa de Calor de Indisponibilidade"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="uhmHostContains">Host (contém)</label>
              <input type="text" class="form-control" id="uhmHostContains" placeholder="Parte do nome do host"/>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="uhmPeriodSubFilter">Período (Sub-filtro)</label>
              <select class="form-select" id="uhmPeriodSubFilter">
                <option value="full_month">Mês completo</option>
                <option value="last_24h">Últimas 24h</option>
                <option value="last_7d">Últimos 7 dias</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="uhmPalette">Paleta de cores</label>
              <select class="form-select" id="uhmPalette">
                <option value="OrRd">OrRd (Laranja/Vermelho)</option>
                <option value="Reds">Reds</option>
                <option value="YlOrRd">YlOrRd</option>
                <option value="PuRd">PuRd</option>
                <option value="viridis">Viridis</option>
                <option value="plasma">Plasma</option>
              </select>
            </div>
            <div class="col-md-6 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="uhmAnnotate" checked>
              <label class="form-check-label" for="uhmAnnotate">Anotar contagens nas células</label>
            </div>
            <div class="col-12">
              <label class="form-label">Severidades</label>
              <div class="d-flex gap-3 flex-wrap">
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevInfo" checked> <label class="form-check-label" for="uhmSevInfo">Informação</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevWarn" checked> <label class="form-check-label" for="uhmSevWarn">Atenção</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevAvg" checked> <label class="form-check-label" for="uhmSevAvg">Média</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevHigh" checked> <label class="form-check-label" for="uhmSevHigh">Alta</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="uhmSevDis" checked> <label class="form-check-label" for="uhmSevDis">Desastre</label></div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveUhmBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeUhmModal');
  }
})();

