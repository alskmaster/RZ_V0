(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['capacity_forecast'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureCapacityForecastModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('cfTitle'),
        itemids: document.getElementById('cfItemIds'),
        valueType: document.getElementById('cfValueType'),
        limit: document.getElementById('cfLimit'),
        projectionDays: document.getElementById('cfProjDays'),
        hideEmpty: document.getElementById('cfHideEmpty'),
        critDays: document.getElementById('cfCritDays'),
        attDays: document.getElementById('cfAttDays'),
        searchQ: document.getElementById('cfSearchQ'),
        searchBtn: document.getElementById('cfSearchBtn'),
        results: document.getElementById('cfResults'),
        addSelected: document.getElementById('cfAddSelected'),
        saveBtn: document.getElementById('saveCFBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      const ids = Array.isArray(o.itemids) ? o.itemids.join(',') : (o.itemids || '');
      el.itemids.value = ids;
      el.valueType.value = String(o.value_type != null ? o.value_type : 0);
      el.limit.value = (o.limit != null ? String(o.limit) : '');
      el.projectionDays.value = String(o.projection_days != null ? o.projection_days : 30);
      el.hideEmpty.checked = !!o.hide_if_empty;
      el.critDays.value = String(o.risk_threshold_critical_days != null ? o.risk_threshold_critical_days : 30);
      el.attDays.value = String(o.risk_threshold_attention_days != null ? o.risk_threshold_attention_days : 90);
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });

      // Search wiring
      if (el.searchBtn && !this._wired) {
        el.searchBtn.addEventListener('click', async ()=>{
          const q = (el.searchQ.value || '').trim();
          const clientId = document.getElementById('client_id')?.value || '0';
          if (!q || !clientId) return;
          try {
            const url = (window.URLS && window.URLS.search_items) ? window.URLS.search_items.replace('0', clientId) + `?q=${encodeURIComponent(q)}` : '';
            const resp = await fetch(url);
            const data = await resp.json();
            const arr = Array.isArray(data.items) ? data.items : [];
            el.results.innerHTML = arr.map(it => `<label class=\"form-check\"><input class=\"form-check-input cf-check\" type=\"checkbox\" value=\"${it.itemid}\"> <span class=\"small\">${it.host} — ${it.name || it.key_} [${it.itemid}]</span></label>`).join('') || '<div class="text-muted small">Nenhum item encontrado.</div>';
          } catch (e) {
            el.results.innerHTML = '<div class="text-danger small">Falha na busca.</div>';
          }
        });
        el.addSelected.addEventListener('click', ()=>{
          const ids = Array.from(el.results.querySelectorAll('.cf-check:checked')).map(i => i.value);
          const cur = (el.itemids.value || '').split(',').map(s=>s.trim()).filter(Boolean);
          const merged = Array.from(new Set(cur.concat(ids)));
          el.itemids.value = merged.join(',');
        });
        this._wired = true;
      }
    },
    save(){
      const el = this.elements;
      const ids = (el.itemids.value || '').split(',').map(s => s.trim()).filter(Boolean);
      const limit = el.limit.value.trim();
      return {
        __title: el.title.value || '',
        itemids: ids,
        value_type: parseInt(el.valueType.value || '0', 10),
        limit: limit === '' ? null : parseFloat(limit),
        projection_days: parseInt(el.projectionDays.value || '30', 10),
        hide_if_empty: !!el.hideEmpty.checked,
        risk_threshold_critical_days: parseInt(el.critDays.value || '30', 10),
        risk_threshold_attention_days: parseInt(el.attDays.value || '90', 10)
      };
    }
  };

  function ensureCapacityForecastModal(){
    let el = document.getElementById('customizeCapacityForecastModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeCapacityForecastModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Previsão de Capacidade</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="cfTitle">Título do módulo</label>
              <input type="text" class="form-control" id="cfTitle" placeholder="Ex: Previsão de Capacidade"/>
            </div>
            <div class="col-12">
              <label class="form-label" for="cfItemIds">ItemIDs (separe por vírgula)</label>
              <textarea class="form-control" id="cfItemIds" rows="3" placeholder="12345,67890"></textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="cfValueType">Tipo de histórico</label>
              <select class="form-select" id="cfValueType">
                <option value="0">Numeric float (0)</option>
                <option value="1">Character (1)</option>
                <option value="2">Log (2)</option>
                <option value="3">Numeric unsigned (3)</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="cfLimit">Limite (para ETA)</label>
              <input type="number" step="any" class="form-control" id="cfLimit" placeholder="Ex: 80"/>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="cfProjDays">Projeção (dias)</label>
              <input type="number" class="form-control" id="cfProjDays" value="30" min="1" />
            </div>
            <div class="col-12">
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="cfHideEmpty">
                <label class="form-check-label" for="cfHideEmpty">Ocultar módulo se não houver itens em risco</label>
              </div>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="cfCritDays">Limite crítico (dias)</label>
              <input type="number" class="form-control" id="cfCritDays" value="30" min="1" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="cfAttDays">Limite de atenção (dias)</label>
              <input type="number" class="form-control" id="cfAttDays" value="90" min="1" />
            </div>
            <hr>
            <div class="col-12">
              <label class="form-label" for="cfSearchQ">Buscar itens (por key)</label>
              <div class="input-group">
                <input type="text" class="form-control" id="cfSearchQ" placeholder="ex: vfs.fs.size[,pused]">
                <button class="btn btn-outline-secondary" type="button" id="cfSearchBtn">Buscar</button>
              </div>
              <div id="cfResults" class="mt-2" style="max-height:180px; overflow:auto;"></div>
              <button type="button" class="btn btn-sm btn-outline-primary mt-2" id="cfAddSelected">Adicionar Selecionados</button>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveCFBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeCapacityForecastModal');
  }
})();
