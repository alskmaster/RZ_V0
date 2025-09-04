(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  function ensureModal(){
    let el = document.getElementById('customizeSlaIncTblModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeSlaIncTblModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Módulo: SLA via Incidentes (Tabela)</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label">Filtrar hosts (contém)</label>
                <input type="text" class="form-control" id="slaIncTblHostFilter" placeholder="ex.: SDWAN" />
              </div>
              <div class="col-12">
                <label class="form-label">Filtrar problema (contém)</label>
                <input type="text" class="form-control" id="slaIncTblProblemFilter" placeholder="ex.: LINK DOWN" />
              </div>
              <div class="col-6">
                <label class="form-label">Casas decimais</label>
                <input type="number" class="form-control" id="slaIncTblDecimals" min="0" max="4" value="2"/>
              </div>
              <div class="col-6">
                <label class="form-label">Ordenar por</label>
                <select class="form-select" id="slaIncTblSortBy">
                  <option value="SLA (%)">SLA (%)</option>
                  <option value="Host">Host</option>
                  <option value="Downtime (s)">Downtime (s)</option>
                </select>
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaIncTblSortAsc" checked>
                <label class="form-check-label" for="slaIncTblSortAsc">Ascendente</label>
              </div>
              <div class="col-6">
                <label class="form-label">Top N</label>
                <input type="number" class="form-control" id="slaIncTblTopN" min="0" value="0"/>
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaIncTblShowDowntime" checked>
                <label class="form-check-label" for="slaIncTblShowDowntime">Exibir Indisponibilidade</label>
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaIncTblShowGoal">
                <label class="form-check-label" for="slaIncTblShowGoal">Exibir coluna Meta</label>
              </div>
              <div class="col-6">
                <label class="form-label">Meta (SLA %)</label>
                <input type="number" class="form-control" id="slaIncTblTarget" min="0" max="100" step="0.1" />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="saveSlaIncTblBtn">Salvar Personalização</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeSlaIncTblModal');
  }

  window.ModuleCustomizers['sla_incidents_table'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        hostFilter: document.getElementById('slaIncTblHostFilter'),
        problemFilter: document.getElementById('slaIncTblProblemFilter'),
        decimals: document.getElementById('slaIncTblDecimals'),
        sortBy: document.getElementById('slaIncTblSortBy'),
        sortAsc: document.getElementById('slaIncTblSortAsc'),
        topN: document.getElementById('slaIncTblTopN'),
        showDown: document.getElementById('slaIncTblShowDowntime'),
        showGoal: document.getElementById('slaIncTblShowGoal'),
        target: document.getElementById('slaIncTblTarget'),
        saveBtn: document.getElementById('saveSlaIncTblBtn')
      };
      // Injeção dinâmica dos checkboxes de severidade (se não existirem no HTML)
      if (!document.getElementById('slaIncTblSevInfo')){
        try{
          const row = document.querySelector('#customizeSlaIncTblModal .row.g-3');
          if (row){
            const sev = document.createElement('div');
            sev.className = 'col-12';
            sev.innerHTML = `
              <label class="form-label">Severidades</label>
              <div class="form-check"><input class="form-check-input" type="checkbox" id="slaIncTblSevInfo"><label class="form-check-label" for="slaIncTblSevInfo">Informação</label></div>
              <div class="form-check"><input class="form-check-input" type="checkbox" id="slaIncTblSevWarning"><label class="form-check-label" for="slaIncTblSevWarning">Atenção</label></div>
              <div class="form-check"><input class="form-check-input" type="checkbox" id="slaIncTblSevAverage"><label class="form-check-label" for="slaIncTblSevAverage">Média</label></div>
              <div class="form-check"><input class="form-check-input" type="checkbox" id="slaIncTblSevHigh"><label class="form-check-label" for="slaIncTblSevHigh">Alta</label></div>
              <div class="form-check"><input class="form-check-input" type="checkbox" id="slaIncTblSevDisaster"><label class="form-check-label" for="slaIncTblSevDisaster">Desastre</label></div>
            `;
            row.insertBefore(sev, row.firstElementChild);
          }
        }catch(e){ /* noop */ }
      }
      // Referências dos checkboxes (podem ter sido injetados agora)
      this.elements.sevInfo = document.getElementById('slaIncTblSevInfo');
      this.elements.sevWarning = document.getElementById('slaIncTblSevWarning');
      this.elements.sevAverage = document.getElementById('slaIncTblSevAverage');
      this.elements.sevHigh = document.getElementById('slaIncTblSevHigh');
      this.elements.sevDisaster = document.getElementById('slaIncTblSevDisaster');
    },
    load(o){
      this._ensure();
      o = o || {};
      this.elements.hostFilter.value = o.host_contains || '';
      this.elements.problemFilter.value = o.problem_contains || '';
      const sev = o.severities || ['high','disaster'];
      if (this.elements.sevInfo) this.elements.sevInfo.checked = sev.includes('info');
      if (this.elements.sevWarning) this.elements.sevWarning.checked = sev.includes('warning');
      if (this.elements.sevAverage) this.elements.sevAverage.checked = sev.includes('average');
      if (this.elements.sevHigh) this.elements.sevHigh.checked = sev.includes('high');
      if (this.elements.sevDisaster) this.elements.sevDisaster.checked = sev.includes('disaster');
      this.elements.decimals.value = o.decimals ?? 2;
      this.elements.sortBy.value = o.sort_by || 'SLA (%)';
      this.elements.sortAsc.checked = (o.sort_asc ?? true);
      this.elements.topN.value = o.top_n ?? 0;
      this.elements.showDown.checked = (o.show_downtime ?? true);
      this.elements.showGoal.checked = !!o.show_goal;
      this.elements.target.value = o.target_sla ?? '';
      this.elements.saveBtn.onclick = null;
      this.elements.saveBtn.addEventListener('click', ()=>{
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once:true });
    },
    save(){
      const severities = [];
      if (this.elements.sevInfo?.checked) severities.push('info');
      if (this.elements.sevWarning?.checked) severities.push('warning');
      if (this.elements.sevAverage?.checked) severities.push('average');
      if (this.elements.sevHigh?.checked) severities.push('high');
      if (this.elements.sevDisaster?.checked) severities.push('disaster');
      return {
        severities,
        host_contains: this.elements.hostFilter.value || '',
        problem_contains: this.elements.problemFilter.value || '',
        decimals: parseInt(this.elements.decimals.value||2),
        sort_by: this.elements.sortBy.value || 'SLA (%)',
        sort_asc: !!this.elements.sortAsc.checked,
        top_n: parseInt(this.elements.topN.value||0),
        show_downtime: !!this.elements.showDown.checked,
        show_goal: !!this.elements.showGoal.checked,
        target_sla: this.elements.target.value ? parseFloat(this.elements.target.value) : null
      };
    }
  };
})();

