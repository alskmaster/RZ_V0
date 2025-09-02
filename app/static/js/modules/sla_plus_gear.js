// Plugin de customização para o módulo SLA Plus VIP
(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  function ensureModal(){
    let el = document.getElementById('customizeSlaPlusModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeSlaPlusModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Módulo: SLA Plus VIP</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-6">
                <label class="form-label">Meta (SLA %)</label>
                <div class="input-group">
                  <input type="number" class="form-control" id="slaPlusTarget" min="0" max="100" step="0.1" />
                  <button class="btn btn-outline-secondary" type="button" id="slaPlusTargetFromClient">Usar do cliente</button>
                </div>
              </div>
              <div class="col-6">
                <label class="form-label">Top N (listas)</label>
                <input type="number" class="form-control" id="slaPlusTopN" min="1" value="10"/>
              </div>
              <div class="col-12 form-check">
                <input class="form-check-input" type="checkbox" id="slaPlusCards" checked>
                <label class="form-check-label" for="slaPlusCards">Exibir cartões de KPIs</label>
              </div>
              <div class="col-12 form-check">
                <input class="form-check-input" type="checkbox" id="slaPlusBelow" checked>
                <label class="form-check-label" for="slaPlusBelow">Listar hosts abaixo da meta</label>
              </div>
              <div class="col-12 form-check">
                <input class="form-check-input" type="checkbox" id="slaPlusReg" checked>
                <label class="form-check-label" for="slaPlusReg">Top regressões</label>
              </div>
              <div class="col-12 form-check">
                <input class="form-check-input" type="checkbox" id="slaPlusImp">
                <label class="form-check-label" for="slaPlusImp">Top melhoras</label>
              </div>
              <div class="col-6">
                <label class="form-label">Limiar de variação (pp)</label>
                <input type="number" class="form-control" id="slaPlusMinDelta" value="0" step="0.1"/>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="saveSlaPlusBtn">Salvar Personalização</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeSlaPlusModal');
  }

  window.ModuleCustomizers['sla_plus'] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        target: document.getElementById('slaPlusTarget'),
        targetBtn: document.getElementById('slaPlusTargetFromClient'),
        topN: document.getElementById('slaPlusTopN'),
        cards: document.getElementById('slaPlusCards'),
        below: document.getElementById('slaPlusBelow'),
        reg: document.getElementById('slaPlusReg'),
        imp: document.getElementById('slaPlusImp'),
        minDelta: document.getElementById('slaPlusMinDelta'),
        saveBtn: document.getElementById('saveSlaPlusBtn')
      };
    },
    load(options){
      this._ensure();
      const o = options || {};
      this.elements.target.value = o.target_sla ?? '';
      this.elements.topN.value = o.top_n ?? 10;
      this.elements.cards.checked = (o.show_cards ?? true);
      this.elements.below.checked = (o.show_below_target ?? true);
      this.elements.reg.checked = (o.show_top_regressions ?? true);
      this.elements.imp.checked = (o.show_top_improvements ?? false);
      this.elements.minDelta.value = o.min_delta ?? 0;
      this.elements.saveBtn.onclick = null;
      if (this.elements.targetBtn){
        this.elements.targetBtn.onclick = () => {
          try{
            const sel=document.getElementById('client_id');
            const opt=sel?.selectedOptions?.[0];
            const sla=opt?.getAttribute('data-sla');
            if (sla) this.elements.target.value = sla;
          }catch(e){}
        };
      }
      this.elements.saveBtn.addEventListener('click', ()=>{
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once:true });
    },
    save(){
      return {
        target_sla: this.elements.target.value ? parseFloat(this.elements.target.value) : null,
        top_n: parseInt(this.elements.topN.value||10),
        show_cards: !!this.elements.cards.checked,
        show_below_target: !!this.elements.below.checked,
        show_top_regressions: !!this.elements.reg.checked,
        show_top_improvements: !!this.elements.imp.checked,
        min_delta: parseFloat(this.elements.minDelta.value||0)
      };
    }
  };
})();

