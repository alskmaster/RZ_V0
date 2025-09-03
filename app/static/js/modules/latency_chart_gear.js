(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};
  window.ModuleCustomizers['latency_chart'] = {
    modal: null,
    elements: {},
    _ensure(){ const el = ensureLatChModal(); if(!this.modal) this.modal=new bootstrap.Modal(el); this.elements={
      host: document.getElementById('latChHostContains'),
      topN: document.getElementById('latChTopN'),
      colorMax: document.getElementById('latChColorMax'),
      colorAvg: document.getElementById('latChColorAvg'),
      colorMin: document.getElementById('latChColorMin'),
      saveBtn: document.getElementById('saveLatChBtn')
    }; },
    load(o){ this._ensure(); o=o||{}; const el=this.elements; el.host.value=o.host_name_contains||''; el.topN.value=o.top_n??0; el.colorMax.value=o.color_max||'#ffb3b3'; el.colorAvg.value=o.color_avg||'#ff6666'; el.colorMin.value=o.color_min||'#cc0000'; el.saveBtn.onclick=null; el.saveBtn.addEventListener('click',()=>{ if(this._onSave) this._onSave(this.save()); this.modal.hide(); },{once:true}); },
    save(){ const el=this.elements; return { host_name_contains: el.host.value||null, top_n: el.topN.value?parseInt(el.topN.value):0, color_max: el.colorMax.value, color_avg: el.colorAvg.value, color_min: el.colorMin.value }; }
  };
  function ensureLatChModal(){ let el=document.getElementById('customizeLatChModal'); if(el) return el; const tpl=document.createElement('div'); tpl.innerHTML=`
  <div class="modal fade" id="customizeLatChModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog"><div class="modal-content">
      <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Latência (Gráficos)</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <div class="mb-3"><label class="form-label" for="latChHostContains">Filtrar hosts (contém)</label>
          <input type="text" class="form-control" id="latChHostContains" placeholder="Parte do nome do host"/></div>
        <div class="row g-3">
          <div class="col-4"><label class="form-label" for="latChTopN">Top N</label><input type="number" class="form-control" id="latChTopN" min="0" value="0"/></div>
          <div class="col-4"><label class="form-label" for="latChColorMax">Cor Máximo</label><input type="color" class="form-control form-control-color" id="latChColorMax" value="#ffb3b3"/></div>
          <div class="col-4"><label class="form-label" for="latChColorAvg">Cor Médio</label><input type="color" class="form-control form-control-color" id="latChColorAvg" value="#ff6666"/></div>
          <div class="col-4"><label class="form-label" for="latChColorMin">Cor Mínimo</label><input type="color" class="form-control form-control-color" id="latChColorMin" value="#cc0000"/></div>
        </div>
      </div>
      <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
        <button type="button" class="btn btn-primary" id="saveLatChBtn">Salvar</button></div>
    </div></div>
  </div>`; document.body.appendChild(tpl.firstElementChild); return document.getElementById('customizeLatChModal'); }
})();

