(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers["traffic_in_table"] = {
    modal: null,
    elements: {},
    _ensure(){
      const modalElement = ensureTrafficInTableModal();
      if (!this.modal) {
        this.modal = new bootstrap.Modal(modalElement);
      }
      this.elements = {
        title: document.getElementById('trafInTbTitle'),
        periodSubFilter: document.getElementById('trafInTbPeriodSubFilter'),
        showSummary: document.getElementById('trafInTbShowSummary'),
        host: document.getElementById('trafInTbHostContains'),
        excludeHosts: document.getElementById('trafInTbExcludeHosts'),
        topN: document.getElementById('trafInTbTopN'),
        sortBy: document.getElementById('trafInTbSortBy'),
        sortAsc: document.getElementById('trafInTbSortAsc'),
        decimals: document.getElementById('trafInTbDecimals'),
        saveBtn: document.getElementById('trafInTbSaveBtn')
      };
    },
    load(options){
      this._ensure();
      const el = this.elements;
      const opts = options || {};
      try {
        el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || '';
      } catch (err) {
        el.title.value = '';
      }
      el.periodSubFilter.value = opts.period_sub_filter || 'full_month';
      if (el.showSummary) {
        el.showSummary.checked = opts.show_summary !== false;
      }
      el.host.value = opts.host_name_contains || '';
      if (el.excludeHosts) {
        el.excludeHosts.value = opts.exclude_hosts_contains || '';
      }
      const topValue = opts.top_n === 0 ? '' : (opts.top_n != null ? opts.top_n : 5);
      el.topN.value = topValue;
      el.sortBy.value = opts.sort_by || 'Avg';
      el.sortAsc.checked = !!opts.sort_asc;
      el.decimals.value = opts.decimals != null ? opts.decimals : 2;

      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', () => {
        if (this._onSave) {
          this._onSave(this.save());
        }
        this.modal.hide();
      }, { once: true });
    },
    save(){
      const el = this.elements;
      const rawTop = (el.topN.value || '').trim();
      const topN = rawTop === '' ? 0 : (parseInt(rawTop, 10) || 0);
      const decimalsVal = parseInt(el.decimals.value, 10);
      return {
        __title: el.title.value || '',
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        show_summary: el.showSummary ? !!el.showSummary.checked : true,
        host_name_contains: el.host.value || null,
        exclude_hosts_contains: el.excludeHosts ? (el.excludeHosts.value || null) : null,
        top_n: topN,
        sort_by: el.sortBy.value || 'Avg',
        sort_asc: !!el.sortAsc.checked,
        decimals: Number.isFinite(decimalsVal) && decimalsVal >= 0 ? decimalsVal : 2
      };
    }
  };

  function ensureTrafficInTableModal(){
    let modal = document.getElementById('customizeTrafficInTableModal');
    if (modal) {
      return modal;
    }
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
    <div class="modal fade" id="customizeTrafficInTableModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Modulo: Trafego de Entrada (Tabela)</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label" for="trafInTbTitle">Titulo do modulo</label>
                <input type="text" class="form-control" id="trafInTbTitle" placeholder="Ex: Trafego de Entrada (Tabela)" />
              </div>
              <div class="col-md-4">
                <label class="form-label" for="trafInTbPeriodSubFilter">Periodo</label>
                <select class="form-select" id="trafInTbPeriodSubFilter">
                  <option value="full_month">Mes Completo</option>
                  <option value="last_7d">Ultimos 7 dias</option>
                  <option value="last_24h">Ultimas 24h</option>
                </select>
              </div>
              <div class="col-md-4 form-check d-flex align-items-end">
                <div>
                  <input class="form-check-input" type="checkbox" id="trafInTbShowSummary" checked>
                  <label class="form-check-label" for="trafInTbShowSummary">Exibir resumo explicativo</label>
                </div>
              </div>
              <div class="col-md-6">
                <label class="form-label" for="trafInTbHostContains">Filtrar hosts (contendo)</label>
                <input type="text" class="form-control" id="trafInTbHostContains" placeholder="Parte do nome do host" />
              </div>
              <div class="col-md-6">
                <label class="form-label" for="trafInTbExcludeHosts">Excluir hosts (contendo)</label>
                <input type="text" class="form-control" id="trafInTbExcludeHosts" placeholder="Lista separada por virgula" />
              </div>
              <div class="col-md-3">
                <label class="form-label" for="trafInTbTopN">Top N</label>
                <input type="number" class="form-control" id="trafInTbTopN" min="0" placeholder="vazio = todos" value="5" />
              </div>
              <div class="col-md-3">
                <label class="form-label" for="trafInTbSortBy">Ordenar por</label>
                <select class="form-select" id="trafInTbSortBy">
                  <option value="Avg">Avg</option>
                  <option value="Max">Max</option>
                  <option value="Min">Min</option>
                </select>
              </div>
              <div class="col-md-3 form-check d-flex align-items-end">
                <div>
                  <input class="form-check-input" type="checkbox" id="trafInTbSortAsc">
                  <label class="form-check-label" for="trafInTbSortAsc">Ascendente</label>
                </div>
              </div>
              <div class="col-md-3">
                <label class="form-label" for="trafInTbDecimals">Casas decimais</label>
                <input type="number" class="form-control" id="trafInTbDecimals" min="0" value="2" />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="trafInTbSaveBtn">Salvar</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(wrapper.firstElementChild);
    return document.getElementById('customizeTrafficInTableModal');
  }
})();
