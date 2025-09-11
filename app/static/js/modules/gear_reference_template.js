(function(){
  // Substitua 'your_module_type' pelo tipo do seu módulo no builder
  const MODULE_TYPE = 'your_module_type';

  window.ModuleCustomizers = window.ModuleCustomizers || {};

  // Exemplo de GEAR baseado no padrão do Incidentes (Tabela)
  window.ModuleCustomizers[MODULE_TYPE] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureGenericGearModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        // Título do módulo
        title: el.querySelector('#genericTitle'),
        // Período
        period: el.querySelector('#genericPeriod'),
        // Filtros
        hostContains: el.querySelector('#genericHostContains'),
        excludeHosts: el.querySelector('#genericExcludeHosts'),
        includeTags: el.querySelector('#genericTagsInclude'),
        excludeTags: el.querySelector('#genericTagsExclude'),
        // Opções
        showDuration: el.querySelector('#genericShowDuration'),
        // Ação
        saveBtn: el.querySelector('#saveGenericCustomizationBtn')
      };
    },
    load(opts){
      this._ensure();
      const o = opts || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      if (el.period) el.period.value = o.period_sub_filter || 'full_month';
      if (el.hostContains) el.hostContains.value = o.host_name_contains || '';
      if (el.excludeHosts) el.excludeHosts.value = o.exclude_hosts_contains || '';
      if (el.includeTags) el.includeTags.value = o.tags_include || '';
      if (el.excludeTags) el.excludeTags.value = o.tags_exclude || '';
      if (el.showDuration) el.showDuration.checked = o.show_duration !== false;
      el.saveBtn && el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      return {
        __title: el.title ? (el.title.value || '') : '',
        period_sub_filter: el.period ? (el.period.value || 'full_month') : 'full_month',
        host_name_contains: el.hostContains ? (el.hostContains.value || null) : null,
        exclude_hosts_contains: el.excludeHosts ? (el.excludeHosts.value || null) : null,
        tags_include: el.includeTags ? (el.includeTags.value || null) : null,
        tags_exclude: el.excludeTags ? (el.excludeTags.value || null) : null,
        show_duration: el.showDuration ? !!el.showDuration.checked : true,
      };
    }
  };

  function ensureGenericGearModal(){
    let el = document.getElementById('genericGearModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="genericGearModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body"><div class="row">
          <div class="col-12">
            <div class="mb-3"><label class="form-label" for="genericTitle">Título do módulo</label>
              <input type="text" class="form-control" id="genericTitle" placeholder="Título exibido no relatório"/>
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3"><label class="form-label" for="genericPeriod">Período</label>
              <select class="form-select" id="genericPeriod">
                <option value="full_month">Mês Completo</option>
                <option value="last_7d">Últimos 7 dias</option>
                <option value="last_24h">Últimas 24h</option>
              </select>
            </div>
            <div class="mb-3"><label class="form-label" for="genericHostContains">Filtrar hosts (contendo)</label>
              <input type="text" class="form-control" id="genericHostContains" placeholder="Parte do nome do host"></div>
            <div class="mb-3"><label class="form-label" for="genericExcludeHosts">Excluir hosts (contendo)</label>
              <input type="text" class="form-control" id="genericExcludeHosts" placeholder="ex: teste, lab"></div>
          </div>
          <div class="col-md-6">
            <div class="mb-3"><label class="form-label" for="genericTagsInclude">Filtrar tags (contendo)</label>
              <input type="text" class="form-control" id="genericTagsInclude" placeholder="ex: service:web, env:prod"></div>
            <div class="mb-3"><label class="form-label" for="genericTagsExclude">Excluir tags (contendo)</label>
              <input type="text" class="form-control" id="genericTagsExclude" placeholder="ex: env:dev"></div>
            <div class="form-check mb-3"><input class="form-check-input" type="checkbox" id="genericShowDuration"><label class="form-check-label" for="genericShowDuration">Mostrar Duração</label></div>
          </div>
        </div></div>
        <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveGenericCustomizationBtn">Salvar</button></div>
      </div></div>
    </div>`;
    try { document.body.appendChild(tpl.firstElementChild); } catch(e) {}
    return document.getElementById('genericGearModal');
  }
})();

