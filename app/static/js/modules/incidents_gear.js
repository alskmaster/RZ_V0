document.addEventListener('DOMContentLoaded', function () {
    if (!window.ModuleCustomizers) {
        window.ModuleCustomizers = {};
    }

    window.ModuleCustomizers.incidents = {
        _ensure: function() {
            const el = ensureIncidentsModal();
            if (!this.modal) this.modal = new bootstrap.Modal(el);
            this.elements = {
                severityInfo: el.querySelector('#incidentsSeverityInfo'),
                severityWarning: el.querySelector('#incidentsSeverityWarning'),
                severityAverage: el.querySelector('#incidentsSeverityAverage'),
                severityHigh: el.querySelector('#incidentsSeverityHigh'),
                severityDisaster: el.querySelector('#incidentsSeverityDisaster'),
                periodSubFilter: el.querySelector('#incidentsPeriodSubFilter'),
                numHosts: el.querySelector('#incidentsNumHosts'),
                showDuration: el.querySelector('#incidentsShowDuration'),
                showAcknowledgements: el.querySelector('#incidentsShowAcknowledgements'),
                primaryGrouping: el.querySelector('#incidentsPrimaryGrouping'),
                saveBtn: el.querySelector('#saveIncidentsCustomizationBtn')
            };
        },

        load: function(options) {
            this._ensure();
            const o = options || {};
            const el = this.elements;

            const defaultSeverities = ['info', 'warning', 'average', 'high', 'disaster'];
            const selectedSeverities = o.severities || defaultSeverities;

            el.severityInfo.checked = selectedSeverities.includes('info');
            el.severityWarning.checked = selectedSeverities.includes('warning');
            el.severityAverage.checked = selectedSeverities.includes('average');
            el.severityHigh.checked = selectedSeverities.includes('high');
            el.severityDisaster.checked = selectedSeverities.includes('disaster');

            el.periodSubFilter.value = o.period_sub_filter || 'full_month';
            el.numHosts.value = o.num_hosts || ''; // Default empty for no limit
            el.showDuration.checked = o.show_duration !== false; // Default true
            el.showAcknowledgements.checked = o.show_acknowledgements !== false; // Default true
            el.primaryGrouping.value = o.primary_grouping || 'host'; // Default to host grouping

            el.saveBtn.addEventListener('click', ()=>{
                if (this._onSave) this._onSave(this.save());
                this.modal.hide();
            }, { once:true });
        },

        save: function() {
            this._ensure();
            const el = this.elements;
            const selectedSeverities = [];

            if (el.severityInfo.checked) selectedSeverities.push('info');
            if (el.severityWarning.checked) selectedSeverities.push('warning');
            if (el.severityAverage.checked) selectedSeverities.push('average');
            if (el.severityHigh.checked) selectedSeverities.push('high');
            if (el.severityDisaster.checked) selectedSeverities.push('disaster');

            return {
                severities: selectedSeverities,
                period_sub_filter: el.periodSubFilter.value,
                num_hosts: el.numHosts.value ? parseInt(el.numHosts.value) : null,
                show_duration: el.showDuration.checked,
                show_acknowledgements: el.showAcknowledgements.checked,
                primary_grouping: el.primaryGrouping.value
            };
        },

    };

    function ensureIncidentsModal(){
        let el = document.getElementById('customizeIncidentsModal');
        if (el) return el;
        const tpl = document.createElement('div');
        tpl.innerHTML = `
            <!-- Modal: Personalização Incidentes -->
            <div class="modal fade" id="customizeIncidentsModal" tabindex="-1" aria-labelledby="customizeIncidentsModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="customizeIncidentsModalLabel">Personalizar Módulo: Incidentes</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="form-label">Filtrar por Severidade:</label>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityInfo">
                                        <label class="form-check-label" for="incidentsSeverityInfo">Informação</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityWarning">
                                        <label class="form-check-label" for="incidentsSeverityWarning">Atenção</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityAverage">
                                        <label class="form-check-label" for="incidentsSeverityAverage">Média</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityHigh">
                                        <label class="form-check-label" for="incidentsSeverityHigh">Alta</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityDisaster">
                                        <label class="form-check-label" for="incidentsSeverityDisaster">Desastre</label>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label for="incidentsPeriodSubFilter" class="form-label">Período (Sub-filtro):</label>
                                        <select class="form-select" id="incidentsPeriodSubFilter">
                                            <option value="full_month">Mês Completo</option>
                                            <option value="last_24h">Últimas 24 Horas</option>
                                            <option value="last_7d">Últimos 7 Dias</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label for="incidentsNumHosts" class="form-label">Número de Hosts (Top N):</label>
                                        <input type="number" class="form-control" id="incidentsNumHosts" min="1" placeholder="Deixe em branco para todos">
                                    </div>
                                    <div class="mb-3">
                                        <label for="incidentsPrimaryGrouping" class="form-label">Agrupamento Principal:</label>
                                        <select class="form-select" id="incidentsPrimaryGrouping">
                                            <option value="host">Por Host</option>
                                            <option value="problem">Por Problema</option>
                                        </select>
                                    </div>
                                    <div class="form-check mb-3">
                                        <input class="form-check-input" type="checkbox" id="incidentsShowDuration">
                                        <label class="form-check-label" for="incidentsShowDuration">Mostrar Duração</label>
                                    </div>
                                    <div class="form-check mb-3">
                                        <input class="form-check-input" type="checkbox" id="incidentsShowAcknowledgements">
                                        <label class="form-check-label" for="incidentsShowAcknowledgements">Mostrar Reconhecimentos</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                            <button type="button" class="btn btn-primary" id="saveIncidentsCustomizationBtn">Salvar Personalização</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(tpl.firstElementChild);
        return document.getElementById('customizeIncidentsModal');
    }
});