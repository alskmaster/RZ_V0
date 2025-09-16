(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};

  window.ModuleCustomizers['softdesk_root_cause'] = {
    _ensure(){
      const el = ensureSoftdeskModal();
      if (!this.modal) this.modal = new bootstrap.Modal(el);
      this.elements = {
        title: el.querySelector('#softdeskTitle'),
        severityInfo: el.querySelector('#softdeskSeverityInfo'),
        severityWarning: el.querySelector('#softdeskSeverityWarning'),
        severityAverage: el.querySelector('#softdeskSeverityAverage'),
        severityHigh: el.querySelector('#softdeskSeverityHigh'),
        severityDisaster: el.querySelector('#softdeskSeverityDisaster'),
        periodSubFilter: el.querySelector('#softdeskPeriodSubFilter'),
        ackFilter: el.querySelector('#softdeskAckFilter'),
        hostContains: el.querySelector('#softdeskHostContains'),
        hostExclude: el.querySelector('#softdeskHostExclude'),
        problemContains: el.querySelector('#softdeskProblemContains'),
        problemExclude: el.querySelector('#softdeskProblemExclude'),
        tagsInclude: el.querySelector('#softdeskTagsInclude'),
        tagsExclude: el.querySelector('#softdeskTagsExclude'),
        topNTickets: el.querySelector('#softdeskTopNTickets'),
        sortBy: el.querySelector('#softdeskSortBy'),
        saveBtn: el.querySelector('#saveSoftdeskCustomizationBtn')
      };
    },
    load(opts){
      this._ensure();
      const o = opts || {};
      const el = this.elements;
      try { el.title.value = (window.currentModuleToCustomize && window.currentModuleToCustomize.title) || ''; } catch (e) {}
      const defaults = ['info','warning','average','high','disaster'];
      const selected = o.severities || defaults;
      el.severityInfo.checked = selected.includes('info');
      el.severityWarning.checked = selected.includes('warning');
      el.severityAverage.checked = selected.includes('average');
      el.severityHigh.checked = selected.includes('high');
      el.severityDisaster.checked = selected.includes('disaster');
      el.periodSubFilter.value = o.period_sub_filter || 'full_month';
      el.ackFilter.value = (o.ack_filter || 'all');
      el.hostContains.value = o.host_name_contains || '';
      el.hostExclude.value = o.exclude_hosts_contains || '';
      el.problemContains.value = o.problem_contains || '';
      el.problemExclude.value = o.exclude_problem_contains || '';
      el.tagsInclude.value = o.tags_include || '';
      el.tagsExclude.value = o.tags_exclude || '';
      const top = o.top_n_tickets;
      el.topNTickets.value = (top !== undefined && top !== null && top !== '') ? top : '';
      el.sortBy.value = (o.sort_by || 'duration');
      el.saveBtn.addEventListener('click', () => {
        if (this._onSave) this._onSave(this.save());
        this.modal.hide();
      }, { once: true });
    },
    save(){
      const el = this.elements;
      const severities = [];
      if (el.severityInfo.checked) severities.push('info');
      if (el.severityWarning.checked) severities.push('warning');
      if (el.severityAverage.checked) severities.push('average');
      if (el.severityHigh.checked) severities.push('high');
      if (el.severityDisaster.checked) severities.push('disaster');
      const hostContains = el.hostContains.value.trim();
      const hostExclude = el.hostExclude.value.trim();
      const problemContains = el.problemContains.value.trim();
      const problemExclude = el.problemExclude.value.trim();
      const tagsInclude = el.tagsInclude.value.trim();
      const tagsExclude = el.tagsExclude.value.trim();
      const topRaw = el.topNTickets.value.trim();
      let topVal = null;
      if (topRaw) {
        const parsed = parseInt(topRaw, 10);
        if (!Number.isNaN(parsed) && parsed > 0) {
          topVal = parsed;
        }
      }
      return {
        __title: el.title ? (el.title.value || '') : '',
        severities,
        period_sub_filter: el.periodSubFilter.value,
        ack_filter: el.ackFilter.value || 'all',
        host_name_contains: hostContains || null,
        exclude_hosts_contains: hostExclude || null,
        problem_contains: problemContains || null,
        exclude_problem_contains: problemExclude || null,
        tags_include: tagsInclude || null,
        tags_exclude: tagsExclude || null,
        top_n_tickets: topVal,
        sort_by: el.sortBy.value || 'duration'
      };
    }
  };

  function ensureSoftdeskModal(){
    let el = document.getElementById('customizeSoftdeskModal');
    if (el) return el;
    const tpl = document.createElement('div');
    tpl.innerHTML = `
    <div class="modal fade" id="customizeSoftdeskModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Personalizar Modulo: Causa-Raiz Softdesk</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label" for="softdeskTitle">Titulo do Modulo</label>
              <input type="text" class="form-control" id="softdeskTitle" placeholder="Ex: Causa-Raiz Softdesk">
            </div>
            <div class="row g-3">
              <div class="col-md-6">
                <h6>Severidades consideradas</h6>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="softdeskSeverityInfo" checked>
                  <label class="form-check-label" for="softdeskSeverityInfo">Informacao</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="softdeskSeverityWarning" checked>
                  <label class="form-check-label" for="softdeskSeverityWarning">Atencao</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="softdeskSeverityAverage" checked>
                  <label class="form-check-label" for="softdeskSeverityAverage">Media</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="softdeskSeverityHigh" checked>
                  <label class="form-check-label" for="softdeskSeverityHigh">Alta</label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="softdeskSeverityDisaster" checked>
                  <label class="form-check-label" for="softdeskSeverityDisaster">Desastre</label>
                </div>
              </div>
              <div class="col-md-6">
                <label class="form-label" for="softdeskPeriodSubFilter">Periodo</label>
                <select class="form-select" id="softdeskPeriodSubFilter">
                  <option value="full_month">Mes completo</option>
                  <option value="last_7d">Ultimos 7 dias</option>
                  <option value="last_24h">Ultimas 24h</option>
                </select>
                <small class="text-muted">Controle o recorte temporal adicional aplicado sobre o periodo do relatorio.</small>
                <div class="mt-3">
                  <label class="form-label" for="softdeskHostContains">Filtrar hosts (contendo)</label>
                  <input type="text" class="form-control" id="softdeskHostContains" placeholder="Parte do nome do host">
                </div>
                <div class="mb-3">
                  <label class="form-label" for="softdeskHostExclude">Excluir hosts (contendo)</label>
                  <input type="text" class="form-control" id="softdeskHostExclude" placeholder="Ex: lab, teste">
                </div>
              </div>
            </div>
            <hr class="my-3">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label" for="softdeskProblemContains">Filtrar problema (contendo)</label>
                <input type="text" class="form-control" id="softdeskProblemContains" placeholder="Parte do titulo do incidente">
              </div>
              <div class="col-md-6">
                <label class="form-label" for="softdeskProblemExclude">Excluir problema (contendo)</label>
                <input type="text" class="form-control" id="softdeskProblemExclude" placeholder="Palavras para remover">
              </div>
            </div>
            <div class="row g-3 mt-1">
              <div class="col-md-6">
                <label class="form-label" for="softdeskTagsInclude">Tags incluir (tag=valor)</label>
                <input type="text" class="form-control" id="softdeskTagsInclude" placeholder="Ex: service=web, env=prod">
                <small class="text-muted">Separe por virgula. Use formato tag=valor.</small>
              </div>
              <div class="col-md-6">
                <label class="form-label" for="softdeskTagsExclude">Tags excluir (tag=valor)</label>
                <input type="text" class="form-control" id="softdeskTagsExclude" placeholder="Ex: env=lab">
              </div>
            </div>
            <hr class="my-3">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label" for="softdeskAckFilter">Filtro de ACK</label>
                <select class="form-select" id="softdeskAckFilter">
                  <option value="all">Todos</option>
                  <option value="only_acked">Somente com ACK</option>
                  <option value="only_unacked">Somente sem ACK</option>
                </select>
              </div>
              <div class="col-md-3">
                <label class="form-label" for="softdeskTopNTickets">Top N tickets</label>
                <input type="number" class="form-control" id="softdeskTopNTickets" min="1" placeholder="Deixe vazio para todos">
              </div>
              <div class="col-md-3">
                <label class="form-label" for="softdeskSortBy">Ordenar por</label>
                <select class="form-select" id="softdeskSortBy">
                  <option value="duration">Maior duracao</option>
                  <option value="tickets">Numero do chamado</option>
                </select>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
            <button type="button" class="btn btn-primary" id="saveSoftdeskCustomizationBtn">Salvar</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(tpl.firstElementChild);
    return document.getElementById('customizeSoftdeskModal');
  }
})();

