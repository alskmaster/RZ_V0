document.addEventListener('DOMContentLoaded', function () {
    if (!window.ModuleCustomizers) {
        window.ModuleCustomizers = {};
    }

    window.ModuleCustomizers.wifi = {
        // Garante que os elementos do DOM foram carregados
        _ensure: function() {
            const el = ensureWifiModal(); // Calls local function to create/get modal HTML
            if (!this.modal) this.modal = new bootstrap.Modal(el); // Initializes Bootstrap modal
            this.elements = {
                chartType: el.querySelector('#wifiChartType'),
                tableType: el.querySelector('#wifiTableType'),
                heatmap: el.querySelector('#wifiHeatmapMode'),
                capacity: el.querySelector('#wifiCapacity'),
                maxCharts: el.querySelector('#wifiMaxCharts'),
                pbLineChart: el.querySelector('#wifiPbLineChart'),
                pbBarCharts: el.querySelector('#wifiPbBarCharts'),
                pbSummaryTable: el.querySelector('#wifiPbSummaryTable'),
                pbDetailedTables: el.querySelector('#wifiPbDetailedTables'),
                pbGlobalHeatmap: el.querySelector('#wifiPbGlobalHeatmap'),
                pbPerApHeatmap: el.querySelector('#wifiPbPerApHeatmap'),
                saveBtn: el.querySelector('#saveWifiCustomizationBtn')
            };
        },

        // Carrega as opções salvas no modal
        load: function(options) {
            this._ensure(); // Calls _ensure
            const o = options || {};
            const el = this.elements; // Use this.elements directly

            el.chartType.value = o.chart || 'bar';
            el.tableType.value = o.table || 'both';
            el.heatmap.value = o.heatmap || 'global';
            el.capacity.value = o.capacity_per_ap != null ? o.capacity_per_ap : 50;
            el.maxCharts.value = o.max_charts != null ? o.max_charts : 6;

            el.pbLineChart.checked = o.pb_line_chart || false;
            el.pbBarCharts.checked = o.pb_bar_charts || false;
            el.pbSummaryTable.checked = o.pb_summary_table || false;
            el.pbDetailedTables.checked = o.pb_detailed_tables || false;
            el.pbGlobalHeatmap.checked = o.pb_global_heatmap || false;
            el.pbPerApHeatmap.checked = o.pb_per_ap_heatmap || false;

            // Add event listener for save button, similar to sla_chart_gear.js
            el.saveBtn.addEventListener('click', ()=>{
                if (this._onSave) this._onSave(this.save());
                this.modal.hide();
            }, { once:true });
        },

        // Salva as opções do modal
        save: function() {
            this._ensure();
            const el = this.elements; // Use this.elements directly

            return {
                chart: el.chartType.value,
                table: el.tableType.value,
                heatmap: el.heatmap.value,
                capacity_per_ap: parseFloat(el.capacity.value),
                max_charts: parseInt(el.maxCharts.value, 10),
                pb_line_chart: el.pbLineChart.checked,
                pb_bar_charts: el.pbBarCharts.checked,
                pb_summary_table: el.pbSummaryTable.checked,
                pb_detailed_tables: el.pbDetailedTables.checked,
                pb_global_heatmap: el.pbGlobalHeatmap.checked,
                pb_per_ap_heatmap: el.pbPerApHeatmap.checked
            };
        },

        };

    function ensureWifiModal(){
      let el = document.getElementById('customizeWifiModal');
      if (el) return el;
      const tpl = document.createElement('div');
      tpl.innerHTML = `
        <!-- Modal: Personalização Wi-Fi -->
        <div class="modal fade" id="customizeWifiModal" tabindex="-1" aria-labelledby="customizeWifiModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="customizeWifiModalLabel">Personalizar Módulo: Wi-Fi (Contagem de Clientes)</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label for="wifiChartType" class="form-label">Gráfico</label>
                                <select id="wifiChartType" class="form-select">
                                    <option value="bar">Barras por AP (máximo diário)</option>
                                    <option value="line">Linha (agregado global)</option>
                                    <option value="both">Ambos</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label for="wifiTableType" class="form-label">Tabela</label>
                                <select id="wifiTableType" class="form-select">
                                    <option value="summary">Resumo (mês atual × anterior)</option>
                                    <option value="detailed">Detalhada por AP e dia</option>
                                    <option value="both">Ambas</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label for="wifiHeatmapMode" class="form-label">Heatmap</label>
                                <select id="wifiHeatmapMode" class="form-select">
                                    <option value="global">Global (média por hora)</option>
                                    <option value="per_ap">Por AP</option>
                                    <option value="both">Ambos</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label for="wifiCapacity" class="form-label">Capacidade/AP</label>
                                <input type="number" id="wifiCapacity" class="form-control" value="50" min="1" step="1">
                                <div class="form-text">Usado para marcar APs saturados (p95 ≥ capacidade).</div>
                            </div>
                            <div class="col-md-3">
                                <label for="wifiMaxCharts" class="form-label">Máx. Gráficos/AP</label>
                                <input type="number" id="wifiMaxCharts" class="form-control" value="6" min="1" step="1">
                            </div>
                        </div>
                        <hr class="my-4">
                        <h6>Quebras de Página</h6>
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="wifiPbLineChart">
                                    <label class="form-check-label" for="wifiPbLineChart">Nova página antes do Gráfico de Linha</label>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="wifiPbBarCharts">
                                    <label class="form-check-label" for="wifiPbBarCharts">Nova página antes dos Gráficos de Barra</label>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="wifiPbSummaryTable">
                                    <label class="form-check-label" for="wifiPbSummaryTable">Nova página antes da Tabela Resumo</label>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="wifiPbDetailedTables">
                                    <label class="form-check-label" for="wifiPbDetailedTables">Nova página antes das Tabelas Detalhadas</label>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="wifiPbGlobalHeatmap">
                                    <label class="form-check-label" for="wifiPbGlobalHeatmap">Nova página antes do Heatmap Global</label>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="wifiPbPerApHeatmap">
                                    <label class="form-check-label" for="wifiPbPerApHeatmap">Nova página antes dos Heatmaps por AP</label>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                        <button type="button" class="btn btn-primary" id="saveWifiCustomizationBtn">Salvar Personalização</button>
                    </div>
                </div>
            </div>
        </div>
        `;
      document.body.appendChild(tpl.firstElementChild);
      return document.getElementById('customizeWifiModal');
    }
});
