(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};
  window.ModuleCustomizers['loss_chart'] = {
    modal: null,
    elements: {},
    _ensure(){ const el=ensureLossChModal(); if(!this.modal) this.modal=new bootstrap.Modal(el);
      if (!document.getElementById('lossChLabelWrap')){
        const body = el.querySelector('.modal-body');
        if (body){
          const wrapDiv = document.createElement('div');
          wrapDiv.className = 'mt-2';
          wrapDiv.innerHTML = '<label class="form-label" for="lossChLabelWrap">Quebra de rótulo (caracteres)</label>'+
                              '<input type="number" class="form-control" id="lossChLabelWrap" min="10" value="45"/>';
          body.appendChild(wrapDiv);
        }
      }
      this.elements={
      host: document.getElementById('lossChHostContains'),
      topN: document.getElementById('lossChTopN'),
      colorMax: document.getElementById('lossChColorMax'),
      colorAvg: document.getElementById('lossChColorAvg'),
      colorMin: document.getElementById('lossChColorMin'),
      labelWrap: document.getElementById('lossChLabelWrap'),
      saveBtn: document.getElementById('saveLossChBtn')
    }; },
    load(o){ this._ensure(); o=o||{}; const el=this.elements; el.host.value=o.host_name_contains||''; el.topN.value=o.top_n??0; el.colorMax.value=o.color_max||'#ffdf80'; el.colorAvg.value=o.color_avg||'#ffc61a'; el.colorMin.value=o.color_min||'#cc9900'; el.saveBtn.onclick=null; el.saveBtn.addEventListener('click',()=>{ if(this._onSave) this._onSave(this.save()); this.modal.hide(); },{once:true}); },
    save(){ const el=this.elements; return { host_name_contains: el.host.value||null, top_n: el.topN.value?parseInt(el.topN.value):0, color_max: el.colorMax.value, color_avg: el.colorAvg.value, color_min: el.colorMin.value, label_wrap: el.labelWrap && el.labelWrap.value ? parseInt(el.labelWrap.value) : 45 }; }
  };
  function ensureLossChModal(){ let el=document.getElementById('customizeLossChModal'); if(el) return el; const tpl=document.createElement('div'); tpl.innerHTML=`
  <div class="modal fade" id="customizeLossChModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog"><div class="modal-content">
      <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: Perda (Gráficos)</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <div class="mb-3"><label class="form-label" for="lossChHostContains">Filtrar hosts (contém)</label>
          <input type="text" class="form-control" id="lossChHostContains" placeholder="Parte do nome do host"/></div>
        <div class="row g-3">
          <div class="col-4"><label class="form-label" for="lossChTopN">Top N</label><input type="number" class="form-control" id="lossChTopN" min="0" value="0"/></div>
          <div class="col-4"><label class="form-label" for="lossChColorMax">Cor Máximo</label><input type="color" class="form-control form-control-color" id="lossChColorMax" value="#ffdf80"/></div>
          <div class="col-4"><label class="form-label" for="lossChColorAvg">Cor Médio</label><input type="color" class="form-control form-control-color" id="lossChColorAvg" value="#ffc61a"/></div>
          <div class="col-4"><label class="form-label" for="lossChColorMin">Cor Mínimo</label><input type="color" class="form-control form-control-color" id="lossChColorMin" value="#cc9900"/></div>
        </div>
      </div>
      <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
        <button type="button" class="btn btn-primary" id="saveLossChBtn">Salvar</button></div>
    </div></div>
  </div>`; document.body.appendChild(tpl.firstElementChild); return document.getElementById('customizeLossChModal'); }
})();
