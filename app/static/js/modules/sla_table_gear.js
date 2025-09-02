// Plugin de customização para o módulo SLA - Tabela
(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  function ensureModal(){
    let el = document.getElementById('customizeSlaTableModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeSlaTableModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Módulo: Tabela de Disponibilidade</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-6">
                <label class="form-label">Meta (SLA %)</label>
                <input type="number" class="form-control" id="slaTableTarget" min="0" max="100" step="0.1" />
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaTableShowGoal">
                <label class="form-check-label" for="slaTableShowGoal">Exibir coluna Meta</label>
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaTableShowDowntime">
                <label class="form-check-label" for="slaTableShowDowntime">Exibir Indisponibilidade</label>
              </div>
              <div class="col-6">
                <label class="form-label">Casas decimais</label>
                <input type="number" class="form-control" id="slaTableDecimals" min="0" max="4" value="2"/>
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaTableHighlight">
                <label class="form-check-label" for="slaTableHighlight">Realçar abaixo da meta</label>
              </div>
              <div class="col-6">
                <label class="form-label">Ordenar por</label>
                <select class="form-select" id="slaTableSortBy">
                  <option value="SLA (%)">SLA (%)</option>
                  <option value="Host">Host</option>
                  <option value="Tempo Indisponível">Tempo Indisponível</option>
                </select>
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaTableSortAsc" checked>
                <label class="form-check-label" for="slaTableSortAsc">Ascendente</label>
              </div>
              <div class="col-6">
                <label class="form-label">Top N</label>
                <input type="number" class="form-control" id="slaTableTopN" min="0" value="0"/>
              </div>
              <div class="col-12 form-check">
                <input class="form-check-input" type="checkbox" id="slaTableOnlyBelow">
                <label class="form-check-label" for="slaTableOnlyBelow">Mostrar apenas hosts abaixo da meta</label>
              </div>
              <div class="col-12 form-check">
                <input class="form-check-input" type="checkbox" id="slaTableHideSummary">
                <label class="form-check-label" for="slaTableHideSummary">Ocultar resumo</label>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="saveSlaTableBtn">Salvar Personalização</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeSlaTableModal');
  }

  window.ModuleCustomizers['sla_table'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        target: document.getElementById('slaTableTarget'),
        showGoal: document.getElementById('slaTableShowGoal'),
        showDown: document.getElementById('slaTableShowDowntime'),
        decimals: document.getElementById('slaTableDecimals'),
        highlight: document.getElementById('slaTableHighlight'),
        sortBy: document.getElementById('slaTableSortBy'),
        sortAsc: document.getElementById('slaTableSortAsc'),
        topN: document.getElementById('slaTableTopN'),
        onlyBelow: document.getElementById('slaTableOnlyBelow'),
        hideSummary: document.getElementById('slaTableHideSummary'),
        saveBtn: document.getElementById('saveSlaTableBtn')
      };
    },
    load(options){
      this._ensure();
      const o = options || {};
      this.elements.target.value = o.target_sla ?? '';
      this.elements.showGoal.checked = !!o.show_goal;
      this.elements.showDown.checked = !!o.show_downtime;
      this.elements.decimals.value = o.decimals ?? 2;
      this.elements.highlight.checked = !!o.highlight_below_goal;
      this.elements.sortBy.value = o.sort_by || 'SLA (%)';
      this.elements.sortAsc.checked = (o.sort_asc ?? true);
      this.elements.topN.value = o.top_n ?? 0;
      this.elements.onlyBelow.checked = !!o.only_below_goal;
      this.elements.hideSummary.checked = !!o.hide_summary;
      this.elements.saveBtn.onclick = null;
      this.elements.saveBtn.addEventListener('click', ()=>{
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once:true });
    },
    save(){
      return {
        target_sla: this.elements.target.value ? parseFloat(this.elements.target.value) : null,
        show_goal: !!this.elements.showGoal.checked,
        show_downtime: !!this.elements.showDown.checked,
        decimals: parseInt(this.elements.decimals.value||2),
        highlight_below_goal: !!this.elements.highlight.checked,
        sort_by: this.elements.sortBy.value || 'SLA (%)',
        sort_asc: !!this.elements.sortAsc.checked,
        top_n: parseInt(this.elements.topN.value||0),
        only_below_goal: !!this.elements.onlyBelow.checked,
        hide_summary: !!this.elements.hideSummary.checked
      };
    }
  };
})();
