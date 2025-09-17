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
                <label class="form-label" id="diskTopNLabel">Top N no gráfico</label>
                <input type="number" class="form-control" id="diskTopN" min="0" value="0" />
              </div>
              <div class="col-md-3 form-check" id="diskShowTableWrapper">
                <input class="form-check-input" type="checkbox" id="diskShowTable" checked>
                <label class="form-check-label" for="diskShowTable">Exibir Tabela</label>
              </div>
              <div class="col-md-3 form-check" id="diskShowChartWrapper">
                <input class="form-check-input" type="checkbox" id="diskShowChart" checked>
                <label class="form-check-label" for="diskShowChart">Exibir Gráfico</label>
              </div>
              <div class="col-md-3" id="diskDecimalsWrapper" style="display: none;">
                <label class="form-label" for="diskDecimals">Casas decimais</label>
                <input type="number" class="form-control" id="diskDecimals" min="0" value="2" />
              </div>
              <div class="col-md-3 form-check" id="diskShowValuesWrapper" style="display: none;">
                <input class="form-check-input" type="checkbox" id="diskShowValues">
                <label class="form-check-label" for="diskShowValues">Mostrar valores</label>
              </div>
              <div class="col-md-3 form-check" id="diskRotateXWrapper" style="display: none;">
                <input class="form-check-input" type="checkbox" id="diskRotateX">
                <label class="form-check-label" for="diskRotateX">Rotacionar rótulos</label>
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

  function createDiskCustomizer(moduleType){
    return {
      modal: null,
      elements: {},
      moduleType,
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
          showTableWrapper: document.getElementById('diskShowTableWrapper'),
          showChartWrapper: document.getElementById('diskShowChartWrapper'),
          topNLabel: document.getElementById('diskTopNLabel'),
          decimalsWrapper: document.getElementById('diskDecimalsWrapper'),
          decimals: document.getElementById('diskDecimals'),
          showValuesWrapper: document.getElementById('diskShowValuesWrapper'),
          showValues: document.getElementById('diskShowValues'),
          rotateXWrapper: document.getElementById('diskRotateXWrapper'),
          rotateX: document.getElementById('diskRotateX'),
          saveBtn: document.getElementById('saveDiskCustomizationBtn'),
        };
      },
      load(options){
        this._ensure();
        const o = options || {};
        const el = this.elements;
        el.preset.value = o.preset || 'auto';
        el.quality.value = o.quality || 'balanced';
        el.hostContains.value = o.host_contains || '';
        el.limitHosts.value = o.limit_hosts || 0;
        el.chunkSize.value = o.chunk_size || 150;
        el.includeRegex.value = o.include_regex || '';
        el.excludeRegex.value = o.exclude_regex || '(?i)(tmpfs|overlay|loop|snap|docker|containerd|kubelet|/proc|/sys|/run|/dev)';
        el.fsSelector.value = o.fs_selector || (o.fast_mode ? 'root_only' : 'root_plus_worst');
        el.percentOnly.checked = (o.percent_only !== false);
        el.fastMode.checked = (o.fast_mode !== false);
        el.topN.value = o.top_n || 0;
        el.showTable.checked = (o.show_table !== false);
        el.showChart.checked = (o.show_chart !== false);
        el.decimals.value = o.decimals != null ? o.decimals : 2;
        el.showValues.checked = !!o.show_values;
        el.rotateX.checked = !!o.rotate_x_labels;

        const applyPreset = () => {
          const preset = el.preset.value;
          const quality = el.quality.value;
          const fsSel = (quality === 'fast') ? 'root_only' : (quality === 'balanced' ? 'root_plus_worst' : 'worst');
          el.fsSelector.value = fsSel;
          if (preset === 'windows') {
            el.includeRegex.value = '^[A-Z]:$';
            el.excludeRegex.value = '';
          } else if (preset === 'linux') {
            el.includeRegex.value = '^/$|^/(var|home|opt|data|srv)$';
            el.excludeRegex.value = '(?i)(tmpfs|overlay|loop|snap|docker|containerd|kubelet|/proc|/sys|/run|/dev)';
          } else if (preset === 'vm') {
            el.includeRegex.value = '(^/$|^/(var|home|opt|data|srv)$)|(^[A-Z]:$)';
            el.excludeRegex.value = '(?i)(tmpfs|overlay|loop|snap|docker|containerd|kubelet|/proc|/sys|/run|/dev)';
          } else if (preset === 'vmware') {
            el.includeRegex.value = '^/vmfs/volumes';
            el.excludeRegex.value = '';
          }
        };
        el.preset.onchange = applyPreset;
        el.quality.onchange = applyPreset;
        // apenas aplicar preset automaticamente na primeira carga quando não há filtros já definidos
        if (!o.include_regex && !o.exclude_regex) {
          applyPreset();
        }

        // Ajusta visibilidade conforme o tipo
        if (this.moduleType === 'disk_table') {
          el.showTableWrapper.style.display = 'none';
          el.showChartWrapper.style.display = 'none';
          el.topNLabel.innerText = 'Limitar linhas (Top N)';
          el.decimalsWrapper.style.display = '';
          el.showValuesWrapper.style.display = 'none';
          el.rotateXWrapper.style.display = 'none';
        } else if (this.moduleType === 'disk_chart') {
          el.showTableWrapper.style.display = 'none';
          el.showChartWrapper.style.display = 'none';
          el.topNLabel.innerText = 'Top N no gráfico';
          el.decimalsWrapper.style.display = 'none';
          el.showValuesWrapper.style.display = '';
          el.rotateXWrapper.style.display = '';
        } else {
          el.showTableWrapper.style.display = '';
          el.showChartWrapper.style.display = '';
          el.topNLabel.innerText = 'Top N no gráfico';
          el.decimalsWrapper.style.display = 'none';
          el.showValuesWrapper.style.display = 'none';
          el.rotateXWrapper.style.display = 'none';
        }

        el.saveBtn.onclick = null;
        el.saveBtn.addEventListener('click', () => {
          if (this._onSave) this._onSave(this.save());
          this.modal.hide();
        }, { once: true });
      },
      save(){
        const el = this.elements;
        const base = {
          preset: el.preset.value,
          quality: el.quality.value,
          host_contains: el.hostContains.value || '',
          limit_hosts: parseInt(el.limitHosts.value || '0', 10),
          chunk_size: parseInt(el.chunkSize.value || '150', 10),
          include_regex: el.includeRegex.value || '',
          exclude_regex: el.excludeRegex.value || '',
          fs_selector: el.fsSelector.value,
          percent_only: !!el.percentOnly.checked,
          fast_mode: !!el.fastMode.checked,
          per_host_limit: (el.fsSelector.value === 'root_plus_worst') ? 2 : 1,
          top_n: parseInt(el.topN.value || '0', 10),
        };
        if (this.moduleType === 'disk') {
          base.show_table = !!el.showTable.checked;
          base.show_chart = !!el.showChart.checked;
        } else {
          base.show_table = this.moduleType === 'disk_table';
          base.show_chart = this.moduleType === 'disk_chart';
          if (this.moduleType === 'disk_table') {
            base.decimals = parseInt(el.decimals.value || '2', 10);
          } else if (this.moduleType === 'disk_chart') {
            base.show_values = !!el.showValues.checked;
            base.rotate_x_labels = !!el.rotateX.checked;
          }
        }
        return base;
      }
    };
  }

  window.ModuleCustomizers['disk'] = createDiskCustomizer('disk');
  window.ModuleCustomizers['disk_table'] = createDiskCustomizer('disk_table');
  window.ModuleCustomizers['disk_chart'] = createDiskCustomizer('disk_chart');
})();
