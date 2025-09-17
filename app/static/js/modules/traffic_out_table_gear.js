(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers["traffic_out_table"] = {
    modal: null,
    elements: {},
    _ensure(){
      const modalElement = ensureTrafficOutTableModal();
      if (!this.modal) {
        this.modal = new bootstrap.Modal(modalElement);
      }
      this.elements = {
        title: document.getElementById('trafOutTbTitle'),
        periodSubFilter: document.getElementById('trafOutTbPeriodSubFilter'),
        showSummary: document.getElementById('trafOutTbShowSummary'),
        host: document.getElementById('trafOutTbHostContains'),
        excludeHosts: document.getElementById('trafOutTbExcludeHosts'),
        topN: document.getElementById('trafOutTbTopN'),
        sortBy: document.getElementById('trafOutTbSortBy'),
        sortAsc: document.getElementById('trafOutTbSortAsc'),
        decimals: document.getElementById('trafOutTbDecimals'),
        saveBtn: document.getElementById('trafOutTbSaveBtn')
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

  function ensureTrafficOutTableModal(){
    let modal = document.getElementById('customizeTrafficOutTableModal');
    if (modal) {
      return modal;
    }
    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
    <div class="modal fade" id="customizeTrafficOutTableModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Modulo: Trafego de Saida (Tabela)</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label" for="trafOutTbTitle">Titulo do modulo</label>
                <input type="text" class="form-control" id="trafOutTbTitle" placeholder="Ex: Trafego de Saida (Tabela)" />
              </div>
              <div class="col-md-4">
                <label class="form-label" for="trafOutTbPeriodSubFilter">Periodo</label>
                <select class="form-select" id="trafOutTbPeriodSubFilter">
                  <option value="full_month">Mes Completo</option>
                  <option value="last_7d">Ultimos 7 dias</option>
                  <option value="last_24h">Ultimas 24h</option>
                </select>
              </div>
              <div class="col-md-4 form-check d-flex align-items-end">
                <div>
                  <input class="form-check-input" type="checkbox" id="trafOutTbShowSummary" checked>
                  <label class="form-check-label" for="trafOutTbShowSummary">Exibir resumo explicativo</label>
                </div>
              </div>
              <div class="col-md-6">
                <label class="form-label" for="trafOutTbHostContains">Filtrar hosts (contendo)</label>
                <input type="text" class="form-control" id="trafOutTbHostContains" placeholder="Parte do nome do host" />
              </div>
              <div class="col-md-6">
                <label class="form-label" for="trafOutTbExcludeHosts">Excluir hosts (contendo)</label>
                <input type="text" class="form-control" id="trafOutTbExcludeHosts" placeholder="Lista separada por virgula" />
              </div>
              <div class="col-md-3">
                <label class="form-label" for="trafOutTbTopN">Top N</label>
                <input type="number" class="form-control" id="trafOutTbTopN" min="0" placeholder="vazio = todos" value="5" />
              </div>
              <div class="col-md-3">
                <label class="form-label" for="trafOutTbSortBy">Ordenar por</label>
                <select class="form-select" id="trafOutTbSortBy">
                  <option value="Avg">Avg</option>
                  <option value="Max">Max</option>
                  <option value="Min">Min</option>
                </select>
              </div>
              <div class="col-md-3 form-check d-flex align-items-end">
                <div>
                  <input class="form-check-input" type="checkbox" id="trafOutTbSortAsc">
                  <label class="form-check-label" for="trafOutTbSortAsc">Ascendente</label>
                </div>
              </div>
              <div class="col-md-3">
                <label class="form-label" for="trafOutTbDecimals">Casas decimais</label>
                <input type="number" class="form-control" id="trafOutTbDecimals" min="0" value="2" />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="trafOutTbSaveBtn">Salvar</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(wrapper.firstElementChild);
    return document.getElementById('customizeTrafficOutTableModal');
  }
})();
