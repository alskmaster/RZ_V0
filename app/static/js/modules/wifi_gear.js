document.addEventListener('DOMContentLoaded', function () {
    if (!window.ModuleCustomizers) {
        window.ModuleCustomizers = {};
    }

    window.ModuleCustomizers.wifi = {
        // Elementos do Modal
        _elements: null,

        // Garante que os elementos do DOM foram carregados
        _ensure: function() {
            if (this._elements) return;
            this._elements = {
                modal: new bootstrap.Modal(document.getElementById('customizeWifiModal')),
                chartType: document.getElementById('wifiChartType'),
                tableType: document.getElementById('wifiTableType'),
                heatmap: document.getElementById('wifiHeatmapMode'),
                capacity: document.getElementById('wifiCapacity'),
                maxCharts: document.getElementById('wifiMaxCharts'),
                // --- Novas Opções de Quebra de Página ---
                pbLineChart: document.getElementById('wifiPbLineChart'),
                pbBarCharts: document.getElementById('wifiPbBarCharts'),
                pbSummaryTable: document.getElementById('wifiPbSummaryTable'),
                pbDetailedTables: document.getElementById('wifiPbDetailedTables'),
                pbGlobalHeatmap: document.getElementById('wifiPbGlobalHeatmap'),
                pbPerApHeatmap: document.getElementById('wifiPbPerApHeatmap'),
                // --- Fim das Novas Opções ---
                saveBtn: document.getElementById('saveWifiCustomizationBtn')
            };
        },

        // Carrega as opções salvas no modal
        load: function(options) {
            this._ensure();
            const el = this._elements;

            el.chartType.value = options.chart || 'bar';
            el.tableType.value = options.table || 'both';
            el.heatmap.value = options.heatmap || 'global';
            el.capacity.value = options.capacity_per_ap != null ? options.capacity_per_ap : 50;
            el.maxCharts.value = options.max_charts != null ? options.max_charts : 6;

            // Carrega estado das checkboxes de quebra de página
            el.pbLineChart.checked = options.pb_line_chart || false;
            el.pbBarCharts.checked = options.pb_bar_charts || false;
            el.pbSummaryTable.checked = options.pb_summary_table || false;
            el.pbDetailedTables.checked = options.pb_detailed_tables || false;
            el.pbGlobalHeatmap.checked = options.pb_global_heatmap || false;
            el.pbPerApHeatmap.checked = options.pb_per_ap_heatmap || false;
        },

        // Salva as opções do modal
        save: function() {
            this._ensure();
            const el = this._elements;

            return {
                chart: el.chartType.value,
                table: el.tableType.value,
                heatmap: el.heatmap.value,
                capacity_per_ap: parseFloat(el.capacity.value),
                max_charts: parseInt(el.maxCharts.value, 10),
                // Salva estado das checkboxes de quebra de página
                pb_line_chart: el.pbLineChart.checked,
                pb_bar_charts: el.pbBarCharts.checked,
                pb_summary_table: el.pbSummaryTable.checked,
                pb_detailed_tables: el.pbDetailedTables.checked,
                pb_global_heatmap: el.pbGlobalHeatmap.checked,
                pb_per_ap_heatmap: el.pbPerApHeatmap.checked
            };
        },

        // Exibe o modal
        show: function() {
            this._ensure();
            this._elements.modal.show();
        }
    };
});
