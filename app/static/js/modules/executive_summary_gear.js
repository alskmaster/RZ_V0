(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['executive_summary'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureExecutiveSummaryModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('esTitle'),
        topN: document.getElementById('esTopN'),
        saveBtn: document.getElementById('saveESBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.topN.value = String((o.top_n_incidents != null ? o.top_n_incidents : 5));
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      return {
        __title: el.title.value || '',
        top_n_incidents: parseInt(el.topN.value || '5', 10)
      };
    }
  };

  function ensureExecutiveSummaryModal(){
    let el = document.getElementById('customizeExecutiveSummaryModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeExecutiveSummaryModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Sumário Executivo</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label" for="esTitle">Título do módulo</label>
            <input type="text" class="form-control" id="esTitle" placeholder="Ex: Sumário Executivo"/>
          </div>
          <div class="mb-3">
            <label class="form-label" for="esTopN">Top N (incidentes por host)</label>
            <input type="number" class="form-control" id="esTopN" value="5" min="1" max="50"/>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveESBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeExecutiveSummaryModal');
  }
})();

