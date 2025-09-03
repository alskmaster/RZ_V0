(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['incidents_table'] = {
    _ensure(){
      const el = ensureIncidentsTableModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        severityInfo: el.querySelector('#incTblSeverityInfo'),
        severityWarning: el.querySelector('#incTblSeverityWarning'),
        severityAverage: el.querySelector('#incTblSeverityAverage'),
        severityHigh: el.querySelector('#incTblSeverityHigh'),
        severityDisaster: el.querySelector('#incTblSeverityDisaster'),
        periodSubFilter: el.querySelector('#incTblPeriodSubFilter'),
        numHosts: el.querySelector('#incTblNumHosts'),
        hostNameContains: el.querySelector('#incTblHostNameContains'),
        primaryGrouping: el.querySelector('#incTblPrimaryGrouping'),
        showDuration: el.querySelector('#incTblShowDuration'),
        showAcknowledgements: el.querySelector('#incTblShowAcknowledgements'),
        saveBtn: el.querySelector('#saveIncTblCustomizationBtn')
      };
    },
    load(opts){
      this._ensure();
      const o = opts || {}; const el = this.elements;
      const def = ['info','warning','average','high','disaster'];
      const sel = o.severities || def;
      el.severityInfo.checked = sel.includes('info');
      el.severityWarning.checked = sel.includes('warning');
      el.severityAverage.checked = sel.includes('average');
      el.severityHigh.checked = sel.includes('high');
      el.severityDisaster.checked = sel.includes('disaster');
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.numHosts.value = o.num_hosts || '';
      el.hostNameContains.value = o.host_name_contains || '';
      el.primaryGrouping.value = o.primary_grouping || 'host';
      el.showDuration.checked = o.show_duration !== false;
      el.showAcknowledgements.checked = o.show_acknowledgements !== false;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements; const severities = [];
      if (el.severityInfo.checked) severities.push('info');
      if (el.severityWarning.checked) severities.push('warning');
      if (el.severityAverage.checked) severities.push('average');
      if (el.severityHigh.checked) severities.push('high');
      if (el.severityDisaster.checked) severities.push('disaster');
      return {
        severities,
        period_sub_filter: el.periodSubFilter.value,
        num_hosts: el.numHosts.value ? parseInt(el.numHosts.value) : null,
        host_name_contains: el.hostNameContains.value || null,
        primary_grouping: el.primaryGrouping.value,
        show_duration: !!el.showDuration.checked,
        show_acknowledgements: !!el.showAcknowledgements.checked,
      };
    }
  };

  function ensureIncidentsTableModal(){
    let el = document.getElementById('customizeIncTblModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeIncTblModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Incidentes (Tabela)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body"><div class="row">
          <div class="col-md-6">
            <label class="form-label">Severidades</label>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incTblSeverityInfo"><label class="form-check-label" for="incTblSeverityInfo">Informação</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incTblSeverityWarning"><label class="form-check-label" for="incTblSeverityWarning">Atenção</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incTblSeverityAverage"><label class="form-check-label" for="incTblSeverityAverage">Média</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incTblSeverityHigh"><label class="form-check-label" for="incTblSeverityHigh">Alta</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incTblSeverityDisaster"><label class="form-check-label" for="incTblSeverityDisaster">Desastre</label></div>
          </div>
          <div class="col-md-6">
            <div class="mb-3"><label class="form-label" for="incTblPeriodSubFilter">Período</label>
              <select class="form-select" id="incTblPeriodSubFilter">
                <option value="full_month">Mês Completo</option>
                <option value="last_24h">Últimas 24h</option>
                <option value="last_7d">Últimos 7 dias</option>
              </select>
            </div>
            <div class="mb-3"><label class="form-label" for="incTblNumHosts">Top N Hosts</label>
              <input type="number" class="form-control" id="incTblNumHosts" min="1"></div>
            <div class="mb-3"><label class="form-label" for="incTblHostNameContains">Filtrar hosts (contém)</label>
              <input type="text" class="form-control" id="incTblHostNameContains" placeholder="Parte do nome do host"></div>
            <div class="mb-3"><label class="form-label" for="incTblPrimaryGrouping">Agrupamento</label>
              <select class="form-select" id="incTblPrimaryGrouping">
                <option value="host">Por Host</option>
                <option value="problem">Por Problema</option>
              </select>
            </div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incTblShowDuration"><label class="form-check-label" for="incTblShowDuration">Mostrar Duração</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="incTblShowAcknowledgements"><label class="form-check-label" for="incTblShowAcknowledgements">Mostrar Reconhecimentos</label></div>
          </div>
        </div></div>
        <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveIncTblCustomizationBtn">Salvar Personalização</button></div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeIncTblModal');
  }
})();
