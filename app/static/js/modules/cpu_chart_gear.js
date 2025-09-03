(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};
  window.ModuleCustomizers['cpu_chart'] = {
    modal: null,
    elements: {},
    _ensure(){ const el=ensureCpuCh(); if(!this.modal) this.modal=new bootstrap.Modal(el); this.elements={
      host: document.getElementById('cpuChHostContains'),
      topN: document.getElementById('cpuChTopN'),
      colorMax: document.getElementById('cpuChColorMax'),
      colorAvg: document.getElementById('cpuChColorAvg'),
      colorMin: document.getElementById('cpuChColorMin'),
      labelWrap: document.getElementById('cpuChLabelWrap'),
      saveBtn: document.getElementById('saveCpuChBtn')
    }; },
    load(o){ this._ensure(); o=o||{}; const el=this.elements; el.host.value=o.host_name_contains||''; el.topN.value=o.top_n??0; el.colorMax.value=o.color_max||'#ff9999'; el.colorAvg.value=o.color_avg||'#ff4d4d'; el.colorMin.value=o.color_min||'#cc0000'; if(el.labelWrap) el.labelWrap.value=o.label_wrap||45; el.saveBtn.onclick=null; el.saveBtn.addEventListener('click',()=>{ if(this._onSave) this._onSave(this.save()); this.modal.hide(); },{once:true}); },
    save(){ const el=this.elements; return { host_name_contains: el.host.value||null, top_n: el.topN.value?parseInt(el.topN.value):0, color_max: el.colorMax.value, color_avg: el.colorAvg.value, color_min: el.colorMin.value, label_wrap: el.labelWrap && el.labelWrap.value ? parseInt(el.labelWrap.value) : 45 }; }
  };
  function ensureCpuCh(){ let el=document.getElementById('customizeCpuChModal'); if(el) return el; const tpl=document.createElement('div'); tpl.innerHTML=`
  <div class="modal fade" id="customizeCpuChModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog"><div class="modal-content">
      <div class="modal-header"><h5 class="modal-title">Personalizar Módulo: CPU (Gráficos)</h5><button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button></div>
      <div class="modal-body">
        <div class="mb-3"><label class="form-label" for="cpuChHostContains">Filtrar hosts (contém)</label><input type="text" class="form-control" id="cpuChHostContains" placeholder="Parte do nome do host"/></div>
        <div class="row g-3">
          <div class="col-4"><label class="form-label" for="cpuChTopN">Top N</label><input type="number" class="form-control" id="cpuChTopN" min="0" value="0"/></div>
          <div class="col-4"><label class="form-label" for="cpuChColorMax">Cor Máximo</label><input type="color" class="form-control form-control-color" id="cpuChColorMax" value="#ff9999"/></div>
          <div class="col-4"><label class="form-label" for="cpuChColorAvg">Cor Médio</label><input type="color" class="form-control form-control-color" id="cpuChColorAvg" value="#ff4d4d"/></div>
          <div class="col-4"><label class="form-label" for="cpuChColorMin">Cor Mínimo</label><input type="color" class="form-control form-control-color" id="cpuChColorMin" value="#cc0000"/></div>
          <div class="col-4"><label class="form-label" for="cpuChLabelWrap">Quebra de rótulo (caracteres)</label><input type="number" class="form-control" id="cpuChLabelWrap" min="10" value="45"/></div>
        </div>
      </div>
      <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button><button type="button" class="btn btn-primary" id="saveCpuChBtn">Salvar</button></div>
    </div></div>
  </div>`; document.body.appendChild(tpl.firstElementChild); return document.getElementById('customizeCpuChModal'); }
})();

