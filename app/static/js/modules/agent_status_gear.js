(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['agent_status'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureAgentStatusModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('asTitle'),
        hostContains: document.getElementById('asHostContains'),
        onlyClientHosts: document.getElementById('asOnlyClientHosts'),
        saveBtn: document.getElementById('saveASBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.hostContains.value = o.host_name_contains || '';
      el.onlyClientHosts.checked = !!o.only_client_hosts;
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      return {
        __title: el.title.value || '',
        host_name_contains: el.hostContains.value || null,
        only_client_hosts: !!el.onlyClientHosts.checked
      };
    }
  };

  function ensureAgentStatusModal(){
    let el = document.getElementById('customizeAgentStatusModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeAgentStatusModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Status do Agente</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label" for="asTitle">Título do módulo</label>
            <input type="text" class="form-control" id="asTitle" placeholder="Ex: Status do Agente Zabbix"/>
          </div>
          <div class="mb-3">
            <label class="form-label" for="asHostContains">Host (contém)</label>
            <input type="text" class="form-control" id="asHostContains" placeholder="Parte do nome do host"/>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="checkbox" id="asOnlyClientHosts"/>
            <label class="form-check-label" for="asOnlyClientHosts">Considerar apenas hosts do cliente</label>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveASBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeAgentStatusModal');
  }
})();

