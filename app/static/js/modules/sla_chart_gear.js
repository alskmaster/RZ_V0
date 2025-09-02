// Plugin de customização para o módulo SLA - Gráfico
(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  function ensureModal(){
    let el = document.getElementById('customizeSlaChartModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeSlaChartModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Módulo: Gráfico de Disponibilidade</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-6">
                <label class="form-label">Top N</label>
                <input type="number" class="form-control" id="slaChartTopN" min="0" value="0"/>
              </div>
              <div class="col-6">
                <label class="form-label">Ordem</label>
                <select class="form-select" id="slaChartOrder">
                  <option value="asc">Ascendente</option>
                  <option value="desc">Descendente</option>
                </select>
              </div>
              <div class="col-6">
                <label class="form-label">Meta (SLA %)</label>
                <input type="number" class="form-control" id="slaChartTarget" min="0" max="100" step="0.1" />
              </div>
              <div class="col-6">
                <label class="form-label">Cor abaixo da meta</label>
                <input type="text" class="form-control" id="slaChartBelowColor" placeholder="#e55353" />
              </div>
              <div class="col-6">
                <label class="form-label">Cor padrão</label>
                <input type="text" class="form-control" id="slaChartColor" placeholder="#2c7be5" />
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaChartAxis" checked>
                <label class="form-check-label" for="slaChartAxis">Eixo 0–100%</label>
              </div>
              <div class="col-12">
                <label class="form-label">Filtrar hosts (contém)</label>
                <input type="text" class="form-control" id="slaChartFilter" placeholder="ex.: SDWAN" />
              </div>
              <hr/>
              <div class="col-6">
                <label class="form-label">Quebra de rótulo</label>
                <input type="number" class="form-control" id="slaChartWrap" value="40" min="10"/>
              </div>
              <div class="col-6">
                <label class="form-label">Altura por barra</label>
                <input type="number" class="form-control" id="slaChartHPB" value="0.35" step="0.05"/>
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaChartDyn" checked>
                <label class="form-check-label" for="slaChartDyn">Altura dinâmica</label>
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaChartValues" checked>
                <label class="form-check-label" for="slaChartValues">Exibir valores</label>
              </div>
              <div class="col-6 form-check">
                <input class="form-check-input" type="checkbox" id="slaChartGrid" checked>
                <label class="form-check-label" for="slaChartGrid">Exibir grid</label>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="saveSlaChartBtn">Salvar Personalização</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeSlaChartModal');
  }

  window.ModuleCustomizers['sla_chart'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        topN: document.getElementById('slaChartTopN'),
        order: document.getElementById('slaChartOrder'),
        target: document.getElementById('slaChartTarget'),
        below: document.getElementById('slaChartBelowColor'),
        color: document.getElementById('slaChartColor'),
        axis: document.getElementById('slaChartAxis'),
        filter: document.getElementById('slaChartFilter'),
        wrap: document.getElementById('slaChartWrap'),
        hpb: document.getElementById('slaChartHPB'),
        dyn: document.getElementById('slaChartDyn'),
        values: document.getElementById('slaChartValues'),
        grid: document.getElementById('slaChartGrid'),
        saveBtn: document.getElementById('saveSlaChartBtn')
      };
    },
    load(options){
      this._ensure();
      const o = options || {};
      this.elements.topN.value = o.top_n ?? 0;
      this.elements.order.value = (o.order || 'asc');
      this.elements.target.value = o.target_sla ?? '';
      this.elements.below.value = o.below_color || '#e55353';
      this.elements.color.value = o.color || '#2c7be5';
      this.elements.axis.checked = (o.x_axis_0_100 ?? true);
      this.elements.filter.value = o.host_contains || '';
      this.elements.wrap.value = o.label_wrap ?? 40;
      this.elements.hpb.value = o.height_per_bar ?? 0.35;
      this.elements.dyn.checked = (o.dynamic_height ?? true);
      this.elements.values.checked = (o.show_values ?? true);
      this.elements.grid.checked = (o.grid ?? true);
      this.elements.saveBtn.onclick = null;
      this.elements.saveBtn.addEventListener('click', ()=>{
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once:true });
    },
    save(){
      return {
        top_n: parseInt(this.elements.topN.value||0),
        order: this.elements.order.value,
        target_sla: this.elements.target.value ? parseFloat(this.elements.target.value) : null,
        below_color: this.elements.below.value || '#e55353',
        color: this.elements.color.value || '#2c7be5',
        x_axis_0_100: !!this.elements.axis.checked,
        host_contains: this.elements.filter.value || '',
        label_wrap: parseInt(this.elements.wrap.value||40),
        height_per_bar: parseFloat(this.elements.hpb.value||0.35),
        dynamic_height: !!this.elements.dyn.checked,
        show_values: !!this.elements.values.checked,
        grid: !!this.elements.grid.checked
      };
    }
  };
})();

