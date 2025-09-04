(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['resilience_panel'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureResiliencePanelModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        titleInput: document.getElementById('resPanelTitle'),
        hostContains: document.getElementById('resPanelHostContains'),
        periodSubFilter: document.getElementById('resPanelPeriodSubFilter'),
        decimals: document.getElementById('resPanelDecimals'),
        highlight: document.getElementById('resPanelHighlight'),
        saveBtn: document.getElementById('saveResiliencePanelBtn')
      };
    },
    load(o){
      this._ensure();
      o = o || {}; const el = this.elements;
      try {
        const curr = window.currentModuleToCustomize || null;
        el.titleInput.value = (curr && curr.title) ? String(curr.title) : '';
      } catch(e) { el.titleInput.value = ''; }
      el.hostContains.value = o.host_name_contains || '';
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.decimals.value = (o.decimals ?? 2);
      el.highlight.checked = (o.highlight_below_goal !== false);
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      return {
        __title: el.titleInput.value || '',
        host_name_contains: el.hostContains.value || null,
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        decimals: el.decimals.value ? parseInt(el.decimals.value, 10) : 2,
        highlight_below_goal: !!el.highlight.checked,
      };
    }
  };

  function ensureResiliencePanelModal(){
    let el = document.getElementById('customizeResiliencePanelModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeResiliencePanelModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Personalizar Módulo: Painel de Resiliência (SLA Preciso)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="resPanelTitle">Título do módulo</label>
              <input type="text" class="form-control" id="resPanelTitle" placeholder="Ex: Painel de Resiliência (SLA Preciso)"/>
            </div>
            <div class="col-md-8">
              <label class="form-label" for="resPanelHostContains">Host (contém)</label>
              <input type="text" class="form-control" id="resPanelHostContains" placeholder="Parte do nome do host"/>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelPeriodSubFilter">Período (Sub-filtro)</label>
              <select class="form-select" id="resPanelPeriodSubFilter">
                <option value="full_month">Mês completo</option>
                <option value="last_24h">Últimas 24h</option>
                <option value="last_7d">Últimos 7 dias</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="resPanelDecimals">Casas decimais (SLA %)</label>
              <input type="number" class="form-control" id="resPanelDecimals" min="0" max="6" value="2"/>
            </div>
            <div class="col-md-4 form-check pt-4">
              <input class="form-check-input" type="checkbox" id="resPanelHighlight" checked>
              <label class="form-check-label" for="resPanelHighlight">Destacar abaixo da meta</label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveResiliencePanelBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeResiliencePanelModal');
  }
})();
