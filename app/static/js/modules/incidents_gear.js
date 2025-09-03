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
                showCharts: el.querySelector('#incidentsShowCharts'),
                chartType: el.querySelector('#incidentsChartType'),
                problemTypeTopN: el.querySelector('#incidentsProblemTypeTopN'),
                dailyVolumeChartType: el.querySelector('#incidentsDailyVolumeChartType'),
                dailyVolumeSeveritySelect: el.querySelector('#incidentsDailyVolumeSeveritySelect'),
                xAxisRotateLabels: el.querySelector('#incidentsXAxisRotateLabels'),
                xAxisAlternateDays: el.querySelector('#incidentsXAxisAlternateDays'),
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

            el.showCharts.checked = o.show_charts !== false; // Default true
            el.chartType.value = o.chart_type || 'severity_pie';
            el.problemTypeTopN.value = o.problem_type_top_n || '';
            el.dailyVolumeChartType.value = o.daily_volume_chart_type || 'bar';
            // Handle multi-select for dailyVolumeSeveritySelect
            Array.from(el.dailyVolumeSeveritySelect.options).forEach(option => {
                option.selected = o.daily_volume_severities && o.daily_volume_severities.includes(option.value);
            });
            el.xAxisRotateLabels.checked = o.x_axis_rotate_labels !== false; // Default true
            el.xAxisAlternateDays.checked = o.x_axis_alternate_days !== false; // Default true

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
                primary_grouping: el.primaryGrouping.value,
                show_charts: el.showCharts.checked,
                chart_type: el.chartType.value,
                problem_type_top_n: el.problemTypeTopN.value ? parseInt(el.problemTypeTopN.value) : null,
                daily_volume_chart_type: el.dailyVolumeChartType.value,
                daily_volume_severities: Array.from(el.dailyVolumeSeveritySelect.selectedOptions).map(option => option.value),
                x_axis_rotate_labels: el.xAxisRotateLabels.checked,
                x_axis_alternate_days: el.xAxisAlternateDays.checked
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
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityInfo" value="info">
                                        <label class="form-check-label" for="incidentsSeverityInfo">Informação</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityWarning" value="warning">
                                        <label class="form-check-label" for="incidentsSeverityWarning">Atenção</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityAverage" value="average">
                                        <label class="form-check-label" for="incidentsSeverityAverage">Média</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityHigh" value="high">
                                        <label class="form-check-label" for="incidentsSeverityHigh">Alta</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="incidentsSeverityDisaster" value="disaster">
                                        <label class="form-check-label" for="incidentsSeverityDisaster">Desastre</label>
                                    </div>
                                    <hr>
                                    <div class="form-check mb-3">
                                        <input class="form-check-input" type="checkbox" id="incidentsShowCharts">
                                        <label class="form-check-label" for="incidentsShowCharts">Exibir Gráficos</label>
                                    </div>
                                    <div class="mb-3">
                                        <label for="incidentsChartType" class="form-label">Tipo de Gráfico:</label>
                                        <select class="form-select" id="incidentsChartType">
                                            <option value="none">Nenhum</option>
                                            <option value="severity_pie">Severidade (Pizza)</option>
                                            <option value="severity_bar">Severidade (Barras)</option>
                                            <option value="problem_type_bar">Tipo de Problema (Barras)</option>
                                            <option value="daily_volume">Volume Diário (Geral)</option>
                                            <option value="daily_volume_severity">Volume Diário (Por Severidade)</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label for="incidentsProblemTypeTopN" class="form-label">Top N Problemas (para gráfico de Tipo de Problema):</label>
                                        <input type="number" class="form-control" id="incidentsProblemTypeTopN" min="1" placeholder="Deixe em branco para todos">
                                    </div>
                                    <div class="mb-3">
                                        <label for="incidentsDailyVolumeChartType" class="form-label">Tipo de Gráfico de Volume Diário:</label>
                                        <select class="form-select" id="incidentsDailyVolumeChartType">
                                            <option value="bar">Barras</option>
                                            <option value="line">Linha</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label for="incidentsDailyVolumeSeveritySelect" class="form-label">Severidades para Gráfico de Volume Diário (Por Severidade):</label>
                                        <select class="form-select" id="incidentsDailyVolumeSeveritySelect" multiple size="5">
                                            <option value="info">Informação</option>
                                            <option value="warning">Atenção</option>
                                            <option value="average">Média</option>
                                            <option value="high">Alta</option>
                                            <option value="disaster">Desastre</option>
                                        </select>
                                        <small class="form-text text-muted">Segure Ctrl/Cmd para selecionar múltiplas.</small>
                                    </div>
                                    <div class="form-check mb-3">
                                        <input class="form-check-input" type="checkbox" id="incidentsXAxisRotateLabels">
                                        <label class="form-check-label" for="incidentsXAxisRotateLabels">Rotacionar Rótulos do Eixo X (45º)</label>
                                    </div>
                                    <div class="form-check mb-3">
                                        <input class="form-check-input" type="checkbox" id="incidentsXAxisAlternateDays">
                                        <label class="form-check-label" for="incidentsXAxisAlternateDays">Dias Alternados no Eixo X</label>
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
                                        <label for="incidentsHostNameContains" class="form-label">Filtrar hosts (contém):</label>
                                        <input type="text" class="form-control" id="incidentsHostNameContains" placeholder="Parte do nome do host">
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