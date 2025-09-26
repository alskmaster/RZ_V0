(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers["incident_availability"] = {
    modal: null,
    elements: {},
    _ensure(){
      const el = ensureIncidentAvailabilityModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: document.getElementById("ia2Title"),
        severities: {
          info: document.getElementById("ia2SevInfo"),
          warning: document.getElementById("ia2SevWarn"),
          average: document.getElementById("ia2SevAvg"),
          high: document.getElementById("ia2SevHigh"),
          disaster: document.getElementById("ia2SevDis"),
          not_classified: document.getElementById("ia2SevNC")
        },
        periodMode: document.getElementById("ia2Period"),
        hostContains: document.getElementById("ia2HostContains"),
        hostExclude: document.getElementById("ia2HostExclude"),
        problemContains: document.getElementById("ia2ProblemContains"),
        problemExclude: document.getElementById("ia2ProblemExclude"),
        tagsInclude: document.getElementById("ia2TagsInclude"),
        tagsExclude: document.getElementById("ia2TagsExclude"),
        groupBy: document.getElementById("ia2GroupBy"),
        topN: document.getElementById("ia2TopN"),
        ackFilter: document.getElementById("ia2AckFilter"),
        targetAvailability: document.getElementById("ia2Target"),
        showDuration: document.getElementById("ia2ShowDuration"),
        showAck: document.getElementById("ia2ShowAck"),
        showDetails: document.getElementById("ia2ShowDetails"),
        showInsight: document.getElementById("ia2ShowInsight"),
        saveBtn: document.getElementById("ia2SaveBtn")
      };
    },
    load(opts){
      this._ensure();
      const o = opts || {};
      const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ""; } catch (err) {}
      const selected = new Set(Array.isArray(o.severities) && o.severities.length ? o.severities : ["info","warning","average","high","disaster"]);
      Object.entries(el.severities).forEach(([key, checkbox]) => {
        if (!checkbox) return;
        checkbox.checked = selected.has(key);
      });
      el.periodMode.value = o.period_mode || "full_month";
      el.hostContains.value = o.host_contains || "";
      el.hostExclude.value = o.host_exclude || "";
      el.problemContains.value = o.problem_contains || "";
      el.problemExclude.value = o.problem_exclude || "";
      el.tagsInclude.value = o.tags_include || "";
      el.tagsExclude.value = o.tags_exclude || "";
      el.groupBy.value = o.group_by || "host";
      el.topN.value = o.top_n_hosts != null ? String(o.top_n_hosts) : "";
      el.ackFilter.value = o.ack_filter || "all";
      el.targetAvailability.value = o.target_availability != null ? String(o.target_availability) : "";
      el.showDuration.checked = o.show_duration !== false;
      el.showAck.checked = Boolean(o.show_acknowledgements);
      el.showDetails.checked = Boolean(o.show_details);
      el.showInsight.checked = o.show_insight !== false;
      el.saveBtn.onclick = null;
      el.saveBtn.addEventListener("click", () => {
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once: true });
    },
    save(){
      const el = this.elements;
      const severities = Object.entries(el.severities)
        .filter(([key, checkbox]) => checkbox && checkbox.checked)
        .map(([key]) => key);
      const topRaw = el.topN.value != null ? el.topN.value.trim() : "";
      let topVal = null;
      if (topRaw) {
        const parsedTop = parseInt(topRaw, 10);
        if (!Number.isNaN(parsedTop) && parsedTop > 0) topVal = parsedTop;
      }
      const targetRaw = el.targetAvailability.value != null ? el.targetAvailability.value.trim() : "";
      const targetVal = targetRaw ? targetRaw : null;
      return {
        __title: el.title.value || "",
        severities: severities.length ? severities : ["info","warning","average","high","disaster"],
        period_mode: el.periodMode.value || "full_month",
        host_contains: el.hostContains.value ? el.hostContains.value.trim() : null,
        host_exclude: el.hostExclude.value ? el.hostExclude.value.trim() : null,
        problem_contains: el.problemContains.value ? el.problemContains.value.trim() : null,
        problem_exclude: el.problemExclude.value ? el.problemExclude.value.trim() : null,
        tags_include: el.tagsInclude.value ? el.tagsInclude.value.trim() : null,
        tags_exclude: el.tagsExclude.value ? el.tagsExclude.value.trim() : null,
        group_by: el.groupBy.value || "host",
        top_n_hosts: topVal,
        ack_filter: el.ackFilter.value || "all",
        target_availability: targetVal,
        show_duration: Boolean(el.showDuration.checked),
        show_acknowledgements: Boolean(el.showAck.checked),
        show_details: Boolean(el.showDetails.checked),
        show_insight: Boolean(el.showInsight.checked)
      };
    }
  };

  function ensureIncidentAvailabilityModal(){
    let el = document.getElementById("customizeIncidentAvailabilityModal");
    if (el) return el;
    const tpl = document.createElement("div");
    tpl.innerHTML = `
    <div class="modal fade" id="customizeIncidentAvailabilityModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-xl"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Personalizar Modulo: Disponibilidade por Incidente</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label" for="ia2Title">Titulo do modulo</label>
              <input type="text" class="form-control" id="ia2Title" placeholder="Ex: Disponibilidade por Incidente" />
            </div>
            <div class="col-lg-6">
              <label class="form-label">Severidades</label>
              <div class="d-flex flex-wrap gap-3">
                <div class="form-check"><input class="form-check-input" type="checkbox" id="ia2SevInfo" checked> <label class="form-check-label" for="ia2SevInfo">Informacao</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="ia2SevWarn" checked> <label class="form-check-label" for="ia2SevWarn">Atencao</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="ia2SevAvg" checked> <label class="form-check-label" for="ia2SevAvg">Media</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="ia2SevHigh" checked> <label class="form-check-label" for="ia2SevHigh">Alta</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="ia2SevDis" checked> <label class="form-check-label" for="ia2SevDis">Desastre</label></div>
                <div class="form-check"><input class="form-check-input" type="checkbox" id="ia2SevNC"> <label class="form-check-label" for="ia2SevNC">Nao classificado</label></div>
              </div>
            </div>
            <div class="col-lg-6">
              <label class="form-label" for="ia2Period">Periodo analisado</label>
              <select class="form-select" id="ia2Period">
                <option value="full_month">Mes Completo</option>
                <option value="last_7d">Ultimos 7 Dias</option>
                <option value="last_24h">Ultimas 24 Horas</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="ia2HostContains">Filtrar hosts (contendo)</label>
              <input type="text" class="form-control" id="ia2HostContains" placeholder="Ex: web,app" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="ia2HostExclude">Excluir hosts (contendo)</label>
              <input type="text" class="form-control" id="ia2HostExclude" placeholder="Ex: teste" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="ia2ProblemContains">Filtrar problema (contendo)</label>
              <input type="text" class="form-control" id="ia2ProblemContains" placeholder="Ex: packet" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="ia2ProblemExclude">Excluir problema (contendo)</label>
              <input type="text" class="form-control" id="ia2ProblemExclude" placeholder="Ex: backup" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="ia2TagsInclude">Filtrar tags (contendo)</label>
              <input type="text" class="form-control" id="ia2TagsInclude" placeholder="Ex: service:web" />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="ia2TagsExclude">Excluir tags (contendo)</label>
              <input type="text" class="form-control" id="ia2TagsExclude" placeholder="Ex: scope:test" />
            </div>
            <div class="col-md-4">
              <label class="form-label" for="ia2GroupBy">Agrupamento</label>
              <select class="form-select" id="ia2GroupBy">
                <option value="host">Por Host</option>
                <option value="problem">Por Problema</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="ia2TopN">Top N Hosts</label>
              <input type="number" class="form-control" id="ia2TopN" min="1" placeholder="Valor ou vazio" />
            </div>
            <div class="col-md-4">
              <label class="form-label" for="ia2AckFilter">Filtro de ACK</label>
              <select class="form-select" id="ia2AckFilter">
                <option value="all">Todos</option>
                <option value="only_acked">Somente com ACK</option>
                <option value="only_unacked">Somente sem ACK</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="ia2Target">Meta de disponibilidade (%)</label>
              <input type="number" class="form-control" id="ia2Target" step="0.01" placeholder="Ex: 99.5" />
            </div>
            <div class="col-md-8 d-flex align-items-end">
              <div class="form-check me-4">
                <input class="form-check-input" type="checkbox" id="ia2ShowDuration" checked>
                <label class="form-check-label" for="ia2ShowDuration">Mostrar duracao</label>
              </div>
              <div class="form-check me-4">
                <input class="form-check-input" type="checkbox" id="ia2ShowAck">
                <label class="form-check-label" for="ia2ShowAck">Mostrar reconhecimentos</label>
              </div>
              <div class="form-check me-4">
                <input class="form-check-input" type="checkbox" id="ia2ShowDetails">
                <label class="form-check-label" for="ia2ShowDetails">Mostrar lista de incidentes</label>
              </div>
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="ia2ShowInsight" checked>
                <label class="form-check-label" for="ia2ShowInsight">Exibir insight executivo</label>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-primary" id="ia2SaveBtn">Salvar</button>
        </div>
      </div></div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById("customizeIncidentAvailabilityModal");
  }
})();