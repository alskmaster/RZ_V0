(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};
  window.ModuleCustomizers['cpu_table'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureCpuTbl();
      if(!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        // gerais
        title: document.getElementById('cpuTblTitle'),
        periodSubFilter: document.getElementById('cpuTblPeriodSubFilter'),
        showSummary: document.getElementById('cpuTblShowSummary'),
        // filtros
        host: document.getElementById('cpuTblHostContains'),
        excludeHosts: document.getElementById('cpuTblExcludeHosts'),
        topN: document.getElementById('cpuTblTopN'),
        // ordenação/decimais
        sortBy: document.getElementById('cpuTblSortBy'),
        sortAsc: document.getElementById('cpuTblSortAsc'),
        decimals: document.getElementById('cpuTblDecimals'),
        // ação
        saveBtn: document.getElementById('saveCpuTblBtn')
      };
    },
    load(o){
      this._ensure(); o=o||{}; const el=this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      if (el.showSummary) el.showSummary.checked = (o.show_summary !== false);
      // filtros
      el.host.value = o.host_name_contains || '';
      if (el.excludeHosts) el.excludeHosts.value = o.exclude_hosts_contains || '';
      el.topN.value = (o.top_n != null && o.top_n !== '') ? o.top_n : 5;
      // ordenação/decimais
      el.sortBy.value = o.sort_by || 'Avg';
      el.sortAsc.checked = !!o.sort_asc;
      el.decimals.value = (o.decimals != null && o.decimals !== '') ? o.decimals : 2;
      // salvar
      el.saveBtn.onclick=null;
      el.saveBtn.addEventListener('click',()=>{ if(this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el=this.elements;
      const tn = el.topN.value === '' ? 0 : (parseInt(el.topN.value, 10) || 0);
      return {
        __title: el.title.value || '',
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        show_summary: el.showSummary ? !!el.showSummary.checked : true,
        host_name_contains: el.host.value||null,
        exclude_hosts_contains: el.excludeHosts ? (el.excludeHosts.value || null) : null,
        sort_by: el.sortBy.value,
        sort_asc: !!el.sortAsc.checked,
        top_n: tn,
        decimals: el.decimals.value ? parseInt(el.decimals.value, 10) : 2
      };
    }
  };

  function ensureCpuTbl(){
    let el=document.getElementById('customizeCpuTblModal');
    if(el) return el;
    const tpl=document.createElement('div');
    tpl.innerHTML=`
  <div class="modal fade" id="customizeCpuTblModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg"><div class="modal-content">
      <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: CPU (Tabela)</h5><button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button></div>
      <div class="modal-body">
        <div class="row g-3">
          <!-- Título -->
          <div class="col-12">
            <label class="form-label" for="cpuTblTitle">Título do módulo</label>
            <input type="text" class="form-control" id="cpuTblTitle" placeholder="Ex: CPU (Tabela)"/>
          </div>
          <!-- Período -->
          <div class="col-md-4">
            <label class="form-label" for="cpuTblPeriodSubFilter">Período</label>
            <select class="form-select" id="cpuTblPeriodSubFilter">
              <option value="full_month">Mês Completo</option>
              <option value="last_7d">Últimos 7 dias</option>
              <option value="last_24h">Últimas 24h</option>
            </select>
          </div>
          <!-- Resumo explicativo -->
          <div class="col-md-4 form-check d-flex align-items-end">
            <div>
              <input class="form-check-input" type="checkbox" id="cpuTblShowSummary" checked>
              <label class="form-check-label" for="cpuTblShowSummary">Exibir resumo explicativo</label>
            </div>
          </div>
          <!-- Filtros de host -->
          <div class="col-md-6">
            <label class="form-label" for="cpuTblHostContains">Filtrar hosts (contendo)</label>
            <input type="text" class="form-control" id="cpuTblHostContains" placeholder="Parte do nome do host"/>
          </div>
          <div class="col-md-6">
            <label class="form-label" for="cpuTblExcludeHosts">Excluir hosts (contendo)</label>
            <input type="text" class="form-control" id="cpuTblExcludeHosts" placeholder="Lista separada por vírgula"/>
          </div>
          <!-- Top N -->
          <div class="col-md-3">
            <label class="form-label" for="cpuTblTopN">Top N</label>
            <input type="number" class="form-control" id="cpuTblTopN" min="0" placeholder="vazio = todos" value="5"/>
          </div>
          <!-- Ordenação -->
          <div class="col-md-3">
            <label class="form-label" for="cpuTblSortBy">Ordenar por</label>
            <select id="cpuTblSortBy" class="form-select">
              <option value="Avg">Avg</option>
              <option value="Max">Max</option>
              <option value="Min">Min</option>
            </select>
          </div>
          <div class="col-md-3 form-check d-flex align-items-end">
            <div>
              <input class="form-check-input" type="checkbox" id="cpuTblSortAsc"/>
              <label class="form-check-label" for="cpuTblSortAsc">Ascendente</label>
            </div>
          </div>
          <!-- Decimais -->
          <div class="col-md-3">
            <label class="form-label" for="cpuTblDecimals">Casas decimais</label>
            <input type="number" class="form-control" id="cpuTblDecimals" min="0" max="4" value="2"/>
          </div>
        </div>
      </div>
      <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button><button type="button" class="btn btn-primary" id="saveCpuTblBtn">Salvar</button></div>
    </div></div>
  </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeCpuTblModal');
  }
})();

