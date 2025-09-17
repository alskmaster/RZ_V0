(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['uptime_summary'] = {
    _ensure(){
      const el = ensureUptimeSummaryModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: el.querySelector('#upSumTitle'),
        hostNameContains: el.querySelector('#upSumHostNameContains'),
        zabbixServiceTag: el.querySelector('#upSumZabbixServiceTag'),
        slaTarget: el.querySelector('#upSumSlaTarget'),
        thresholdWarning: el.querySelector('#upSumThresholdWarning'),
        thresholdCritical: el.querySelector('#upSumThresholdCritical'),
        sortBy: el.querySelector('#upSumSortBy'),
        saveBtn: el.querySelector('#saveUpSumCustomizationBtn')
      };
    },
    load(opts){
      this._ensure();
      const o = opts || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.hostNameContains.value = o.host_name_contains || '';
      el.zabbixServiceTag.value = o.zabbix_service_tag || '';
      el.slaTarget.value = o.sla_target != null ? o.sla_target : '99.9';
      el.thresholdWarning.value = o.threshold_warning != null ? o.threshold_warning : '99.95';
      el.thresholdCritical.value = o.threshold_critical != null ? o.threshold_critical : '99.9';
      el.sortBy.value = o.sort_by || 'hostname_asc';
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      return {
        __title: el.title ? (el.title.value || '') : '',
        host_name_contains: el.hostNameContains.value || null,
        zabbix_service_tag: el.zabbixServiceTag.value || null,
        sla_target: parseFloat(el.slaTarget.value) || 99.9,
        threshold_warning: parseFloat(el.thresholdWarning.value) || 99.95,
        threshold_critical: parseFloat(el.thresholdCritical.value) || 99.9,
        sort_by: el.sortBy.value,
      };
    }
  };

  function ensureUptimeSummaryModal(){
    let el = document.getElementById('customizeUpSumModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeUpSumModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Modulo: Resumo de Disponibilidade</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body"><div class="row g-3">
          <div class="col-12">
            <div class="mb-3"><label class="form-label" for="upSumTitle">Titulo do Modulo</label>
              <input type="text" class="form-control" id="upSumTitle" placeholder="Ex: Uptime dos Servidores Criticos"/>
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3"><label class="form-label" for="upSumHostNameContains">Filtrar hosts (contendo)</label>
              <input type="text" class="form-control" id="upSumHostNameContains" placeholder="Parte do nome do host"></div>
            <div class="mb-3"><label class="form-label" for="upSumZabbixServiceTag">Filtrar por Tag de Servico Zabbix</label>
              <input type="text" class="form-control" id="upSumZabbixServiceTag" placeholder="Ex: Business:ERP (opcional)">
              <div class="form-text">Usado para selecionar os servicos Zabbix corretos para calculo de SLA.</div>
            </div>
            <div class="mb-3"><label class="form-label" for="upSumSortBy">Ordenar hosts por</label>
              <select class="form-select" id="upSumSortBy">
                <option value="hostname_asc">Nome do Host (A-Z)</option>
                <option value="uptime_asc">Pior Uptime</option>
                <option value="downtime_desc">Maior Tempo de Indisponibilidade</option>
              </select>
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3"><label class="form-label" for="upSumSlaTarget">Meta de SLA (%)</label>
              <input type="number" step="0.001" class="form-control" id="upSumSlaTarget" value="99.9"></div>
            <div class="mb-3"><label class="form-label" for="upSumThresholdWarning">Limiar de Alerta (% Uptime)</label>
              <input type="number" step="0.001" class="form-control" id="upSumThresholdWarning" value="99.95"></div>
            <div class="mb-3"><label class="form-label" for="upSumThresholdCritical">Limiar Critico (% Uptime)</label>
              <input type="number" step="0.001" class="form-control" id="upSumThresholdCritical" value="99.9"></div>
          </div>
        </div></div>
        <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveUpSumCustomizationBtn">Salvar</button></div>
      </div></div>
    </div>`;
    try { document.body.appendChild(tpl.firstElementChild); } catch(e) {}
    return document.getElementById('customizeUpSumModal');
  }
})();
