import pandas as pd

from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart
from .disk_shared import collect_disk_dataframe


class DiskCollector(BaseCollector):
    """Coletor legado que exibe tabela e gr?fico juntos (compatibilidade)."""

    def collect(self, all_hosts, period):
        df_disk, warning = collect_disk_dataframe(self.generator, self.module_config, all_hosts, period)
        if df_disk.empty:
            return "<p><i>N?o foram encontrados dados de disco para os hosts e per?odo selecionados.</i></p>"

        opts = self.module_config.get('custom_options', {}) or {}
        show_table = opts.get('show_table', True)
        show_chart = opts.get('show_chart', True)
        top_n = int(opts.get('top_n', 0) or 0)

        module_data = {'tabela': None, 'grafico': None}
        if show_table:
            df_table = df_disk.rename(columns={'Host': 'Host', 'Filesystem': 'Filesystem', 'Min': 'M?nimo (%)', 'Avg': 'M?dio (%)', 'Max': 'M?ximo (%)'})
            module_data['tabela'] = df_table.to_html(classes='table', index=False, float_format='%.2f')
        if show_chart:
            df_chart = df_disk.copy()
            if top_n > 0:
                df_chart = df_chart.sort_values(by='Avg', ascending=False).head(top_n)
            module_data['grafico'] = generate_multi_bar_chart(
                df_chart,
                'Uso de Disco (%) - Pior FS por Host',
                'Uso de Disco (%)',
                ['#d1b3ff', '#a366ff', '#7a1aff']
            )
        return self.render('disk', module_data)
