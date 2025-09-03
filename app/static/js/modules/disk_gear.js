// Plugin de customização para o módulo Uso de Disco
(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  function ensureModal(){
    let el = document.getElementById('customizeDiskModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeDiskModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Módulo: Uso de Disco</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Filtrar hosts (contém)</label>
                <input type="text" class="form-control" id="diskHostContains" placeholder="ex.: SRV, DB, APP" />
              </div>
              <div class="col-md-3">
                <label class="form-label">Limitar hosts (Top N)</label>
                <input type="number" class="form-control" id="diskLimitHosts" min="0" value="0" />
              </div>
              <div class="col-md-3">
                <label class="form-label">Chunk size (avançado)</label>
                <input type="number" class="form-control" id="diskChunkSize" min="50" value="150" />
              </div>

              <div class="col-12">
                <label class="form-label">Incluir FS (regex)</label>
                <input type="text" class="form-control" id="diskIncludeRegex" placeholder="ex.: ^/($|var|home)|^[A-Z]:$" />
              </div>
              <div class="col-12">
                <label class="form-label">Excluir FS (regex)</label>
                <input type="text" class="form-control" id="diskExcludeRegex" value="(?i)(tmpfs|overlay|loop|snap|docker|containerd|kubelet|/proc|/sys|/run|/dev)" />
                <div class="form-text">Padrões efêmeros já preenchidos para reduzir ruído e carga.</div>
              </div>

              <div class="col-md-6">
                <label class="form-label">Seleção por host</label>
                <select class="form-select" id="diskFsSelector">
                  <option value="root_only">Apenas raiz (/, C:, D:)</option>
                  <option value="worst">Pior FS por host (padrão clássico)</option>
                </select>
              </div>
              <div class="col-md-3 form-check">
                <input class="form-check-input" type="checkbox" id="diskPercentOnly" checked>
                <label class="form-check-label" for="diskPercentOnly">Somente percentuais (pused/pfree)</label>
              </div>
              <div class="col-md-3 form-check">
                <input class="form-check-input" type="checkbox" id="diskFastMode" checked>
                <label class="form-check-label" for="diskFastMode">Modo rápido (raiz por host)</label>
              </div>

              <hr/>
              <div class="col-md-3">
                <label class="form-label">Top N no gráfico</label>
                <input type="number" class="form-control" id="diskTopN" min="0" value="0" />
              </div>
              <div class="col-md-3 form-check">
                <input class="form-check-input" type="checkbox" id="diskShowTable" checked>
                <label class="form-check-label" for="diskShowTable">Exibir Tabela</label>
              </div>
              <div class="col-md-3 form-check">
                <input class="form-check-input" type="checkbox" id="diskShowChart" checked>
                <label class="form-check-label" for="diskShowChart">Exibir Gráfico</label>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="saveDiskCustomizationBtn">Salvar</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeDiskModal');
  }

  window.ModuleCustomizers['disk'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        hostContains: document.getElementById('diskHostContains'),
        limitHosts: document.getElementById('diskLimitHosts'),
        chunkSize: document.getElementById('diskChunkSize'),
        includeRegex: document.getElementById('diskIncludeRegex'),
        excludeRegex: document.getElementById('diskExcludeRegex'),
        fsSelector: document.getElementById('diskFsSelector'),
        percentOnly: document.getElementById('diskPercentOnly'),
        fastMode: document.getElementById('diskFastMode'),
        topN: document.getElementById('diskTopN'),
        showTable: document.getElementById('diskShowTable'),
        showChart: document.getElementById('diskShowChart'),
        saveBtn: document.getElementById('saveDiskCustomizationBtn'),
      };
    },
    load(options){
      this._ensure();
      const o = options || {};
      this.elements.hostContains.value = o.host_contains || '';
      this.elements.limitHosts.value = o.limit_hosts || 0;
      this.elements.chunkSize.value = o.chunk_size || 150;
      this.elements.includeRegex.value = o.include_regex || '';
      this.elements.excludeRegex.value = o.exclude_regex || '(?i)(tmpfs|overlay|loop|snap|docker|containerd|kubelet|/proc|/sys|/run|/dev)';
      this.elements.fsSelector.value = o.fs_selector || (o.fast_mode ? 'root_only' : 'worst') || 'root_only';
      this.elements.percentOnly.checked = (o.percent_only !== false);
      this.elements.fastMode.checked = (o.fast_mode !== false);
      this.elements.topN.value = o.top_n || 0;
      this.elements.showTable.checked = (o.show_table !== false);
      this.elements.showChart.checked = (o.show_chart !== false);
      // wire save
      this.elements.saveBtn.onclick = null;
      this.elements.saveBtn.addEventListener('click', ()=>{
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once:true });
    },
    save(){
      return {
        host_contains: this.elements.hostContains.value || '',
        limit_hosts: parseInt(this.elements.limitHosts.value || '0', 10),
        chunk_size: parseInt(this.elements.chunkSize.value || '150', 10),
        include_regex: this.elements.includeRegex.value || '',
        exclude_regex: this.elements.excludeRegex.value || '',
        fs_selector: this.elements.fsSelector.value,
        percent_only: !!this.elements.percentOnly.checked,
        fast_mode: !!this.elements.fastMode.checked,
        top_n: parseInt(this.elements.topN.value || '0', 10),
        show_table: !!this.elements.showTable.checked,
        show_chart: !!this.elements.showChart.checked,
      };
    }
  };
})();
