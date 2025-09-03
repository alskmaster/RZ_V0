(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['mem_table'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureMemTableModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        host: document.getElementById('memTblHostContains'),
        sortBy: document.getElementById('memTblSortBy'),
        sortAsc: document.getElementById('memTblSortAsc'),
        topN: document.getElementById('memTblTopN'),
        decimals: document.getElementById('memTblDecimals'),
        saveBtn: document.getElementById('saveMemTblBtn')
      };
    },
    load(o){
      this._ensure(); o = o||{}; const el = this.elements;
      el.host.value = o.host_name_contains || '';
      el.sortBy.value = o.sort_by || 'Avg';
      el.sortAsc.checked = !!o.sort_asc;
      el.topN.value = o.top_n ?? 0;
      el.decimals.value = o.decimals ?? 2;
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });
    },
    save(){
      const el = this.elements;
      return {
        host_name_contains: el.host.value || null,
        sort_by: el.sortBy.value,
        sort_asc: !!el.sortAsc.checked,
        top_n: el.topN.value ? parseInt(el.topN.value) : 0,
        decimals: el.decimals.value ? parseInt(el.decimals.value) : 2,
      };
    }
  };

  function ensureMemTableModal(){
    let el = document.getElementById('customizeMemTblModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeMemTblModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Memória (Tabela)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label" for="memTblHostContains">Filtrar hosts (contém)</label>
            <input type="text" class="form-control" id="memTblHostContains" placeholder="Parte do nome do host"/>
          </div>
          <div class="row g-3">
            <div class="col-6">
              <label class="form-label" for="memTblSortBy">Ordenar por</label>
              <select id="memTblSortBy" class="form-select">
                <option value="Avg">Avg</option>
                <option value="Max">Max</option>
                <option value="Min">Min</option>
              </select>
            </div>
            <div class="col-6 form-check">
              <input class="form-check-input" type="checkbox" id="memTblSortAsc"/>
              <label class="form-check-label" for="memTblSortAsc">Ascendente</label>
            </div>
            <div class="col-6">
              <label class="form-label" for="memTblTopN">Top N</label>
              <input type="number" class="form-control" id="memTblTopN" min="0" value="0"/>
            </div>
            <div class="col-6">
              <label class="form-label" for="memTblDecimals">Casas decimais</label>
              <input type="number" class="form-control" id="memTblDecimals" min="0" max="4" value="2"/>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveMemTblBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeMemTblModal');
  }
})();

