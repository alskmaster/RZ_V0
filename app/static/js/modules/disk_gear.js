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
            <div class="alert alert-info small">
              Selecione o perfil do ambiente e a qualidade para equilibrar velocidade e detalhe.
            </div>
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Perfil de Ambiente</label>
                <select class="form-select" id="diskPreset">
                  <option value="auto">Auto</option>
                  <option value="windows">Windows (drives C:, D:, ...)</option>
                  <option value="linux">Linux (/, /var, /home, ...)</option>
                  <option value="vm">VM (Windows/Linux)</option>
                  <option value="vmware">VMware/ESXi (datastores)</option>
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label">Qualidade</label>
                <select class="form-select" id="diskQuality">
                  <option value="fast">Rápido (raiz por host)</option>
                  <option value="balanced" selected>Equilíbrio (raiz + pior FS)</option>
                  <option value="full">Completo (pior FS por host)</option>
                </select>
              </div>
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
                  <option value="root_plus_worst" selected>Raiz + pior FS</option>
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
        preset: document.getElementById('diskPreset'),
        quality: document.getElementById('diskQuality'),
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
      this.elements.preset.value = o.preset || 'auto';
      this.elements.quality.value = o.quality || 'balanced';
      this.elements.hostContains.value = o.host_contains || '';
      this.elements.limitHosts.value = o.limit_hosts || 0;
      this.elements.chunkSize.value = o.chunk_size || 150;
      this.elements.includeRegex.value = o.include_regex || '';
      this.elements.excludeRegex.value = o.exclude_regex || '(?i)(tmpfs|overlay|loop|snap|docker|containerd|kubelet|/proc|/sys|/run|/dev)';
      this.elements.fsSelector.value = o.fs_selector || (o.fast_mode ? 'root_only' : 'root_plus_worst');
      this.elements.percentOnly.checked = (o.percent_only !== false);
      this.elements.fastMode.checked = (o.fast_mode !== false);
      this.elements.topN.value = o.top_n || 0;
      this.elements.showTable.checked = (o.show_table !== false);
      this.elements.showChart.checked = (o.show_chart !== false);
      // wire save
      const applyPreset = () => {
        const p = this.elements.preset.value;
        const q = this.elements.quality.value;
        const fsSel = (q === 'fast') ? 'root_only' : (q === 'balanced' ? 'root_plus_worst' : 'worst');
        this.elements.fsSelector.value = fsSel;
        if (p === 'windows') {
          this.elements.includeRegex.value = '^[A-Z]:$';
          this.elements.excludeRegex.value = '';
        } else if (p === 'linux') {
          this.elements.includeRegex.value = '^/$|^/(var|home|opt|data|srv)$';
          this.elements.excludeRegex.value = '(?i)(tmpfs|overlay|loop|snap|docker|containerd|kubelet|/proc|/sys|/run|/dev)';
        } else if (p === 'vm') {
          this.elements.includeRegex.value = '(^/$|^/(var|home|opt|data|srv)$)|(^[A-Z]:$)';
          this.elements.excludeRegex.value = '(?i)(tmpfs|overlay|loop|snap|docker|containerd|kubelet|/proc|/sys|/run|/dev)';
        } else if (p === 'vmware') {
          this.elements.includeRegex.value = '^/vmfs/volumes';
          this.elements.excludeRegex.value = '';
        }
      };
      this.elements.preset.onchange = applyPreset;
      this.elements.quality.onchange = applyPreset;
      applyPreset();
      this.elements.saveBtn.onclick = null;
      this.elements.saveBtn.addEventListener('click', ()=>{
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once:true });
    },
    save(){
      return {
        preset: this.elements.preset.value,
        quality: this.elements.quality.value,
        host_contains: this.elements.hostContains.value || '',
        limit_hosts: parseInt(this.elements.limitHosts.value || '0', 10),
        chunk_size: parseInt(this.elements.chunkSize.value || '150', 10),
        include_regex: this.elements.includeRegex.value || '',
        exclude_regex: this.elements.excludeRegex.value || '',
        fs_selector: this.elements.fsSelector.value,
        percent_only: !!this.elements.percentOnly.checked,
        fast_mode: !!this.elements.fastMode.checked,
        per_host_limit: (this.elements.fsSelector.value === 'root_plus_worst') ? 2 : 1,
        top_n: parseInt(this.elements.topN.value || '0', 10),
        show_table: !!this.elements.showTable.checked,
        show_chart: !!this.elements.showChart.checked,
      };
    }
  };
})();
