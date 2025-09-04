(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['critical_performance'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureCriticalPerformanceModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById('cpTitle'),
        itemids: document.getElementById('cpItemIds'),
        valueType: document.getElementById('cpValueType'),
        periodSubFilter: document.getElementById('cpPeriodSubFilter'),
        hideEmpty: document.getElementById('cpHideEmpty'),
        minPoints: document.getElementById('cpMinPoints'),
        searchQ: document.getElementById('cpSearchQ'),
        searchBtn: document.getElementById('cpSearchBtn'),
        results: document.getElementById('cpResults'),
        addSelected: document.getElementById('cpAddSelected'),
        saveBtn: document.getElementById('saveCPBtn')
      };
    },
    load(o){
      this._ensure(); o = o || {}; const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch(e) {}
      const ids = Array.isArray(o.itemids) ? o.itemids.join(',') : (o.itemids || '');
      el.itemids.value = ids;
      el.valueType.value = String(o.value_type != null ? o.value_type : 0);
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.hideEmpty.checked = !!o.hide_if_empty;
      el.minPoints.value = String(o.min_points != null ? o.min_points : 10);
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener('click', ()=>{ if (this._onSave) this._onSave(this.save()); this.modal.hide(); }, { once:true });

      // Search wiring (optional)
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
            el.results.innerHTML = arr.map(it => `<label class=\"form-check\"><input class=\"form-check-input cp-check\" type=\"checkbox\" value=\"${it.itemid}\"> <span class=\"small\">${it.host} — ${it.name || it.key_} [${it.itemid}]</span></label>`).join('') || '<div class="text-muted small">Nenhum item encontrado.</div>';
          } catch (e) {
            el.results.innerHTML = '<div class="text-danger small">Falha na busca.</div>';
          }
        });
        el.addSelected.addEventListener('click', ()=>{
          const ids = Array.from(el.results.querySelectorAll('.cp-check:checked')).map(i => i.value);
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
      return {
        __title: el.title.value || '',
        itemids: ids,
        value_type: parseInt(el.valueType.value || '0', 10),
        period_sub_filter: el.periodSubFilter.value || 'full_month',
        hide_if_empty: !!el.hideEmpty.checked,
        min_points: parseInt(el.minPoints.value || '10', 10)
      };
    }
  };

  function ensureCriticalPerformanceModal(){
    let el = document.getElementById('customizeCriticalPerformanceModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeCriticalPerformanceModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Desempenho Crítico</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="cpTitle">Título do módulo</label>
              <input type="text" class="form-control" id="cpTitle" placeholder="Ex: Desempenho Crítico"/>
            </div>
            <div class="col-12">
              <label class="form-label" for="cpItemIds">ItemIDs (separe por vírgula)</label>
              <textarea class="form-control" id="cpItemIds" rows="3" placeholder="12345,67890"></textarea>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="cpValueType">Tipo de histórico</label>
              <select class="form-select" id="cpValueType">
                <option value="0">Numeric float (0)</option>
                <option value="1">Character (1)</option>
                <option value="2">Log (2)</option>
                <option value="3">Numeric unsigned (3)</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="cpPeriodSubFilter">Período (sub-filtro)</label>
              <select class="form-select" id="cpPeriodSubFilter">
                <option value="full_month">Mês completo</option>
                <option value="last_24h">Últimas 24h</option>
                <option value="last_7d">Últimos 7 dias</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="cpMinPoints">Mín. pontos por série</label>
              <input type="number" class="form-control" id="cpMinPoints" value="10" min="1"/>
            </div>
            <div class="col-12">
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="cpHideEmpty">
                <label class="form-check-label" for="cpHideEmpty">Ocultar módulo se não houver séries ativas</label>
              </div>
            </div>
            <hr>
            <div class="col-12">
              <label class="form-label" for="cpSearchQ">Buscar itens (por key)</label>
              <div class="input-group">
                <input type="text" class="form-control" id="cpSearchQ" placeholder="ex: system.cpu.util">
                <button class="btn btn-outline-secondary" type="button" id="cpSearchBtn">Buscar</button>
              </div>
              <div id="cpResults" class="mt-2" style="max-height:180px; overflow:auto;"></div>
              <button type="button" class="btn btn-sm btn-outline-primary mt-2" id="cpAddSelected">Adicionar Selecionados</button>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="saveCPBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeCriticalPerformanceModal');
  }
})();
