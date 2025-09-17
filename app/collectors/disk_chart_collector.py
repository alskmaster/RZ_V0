# app/collectors/disk_chart_collector.py
import datetime as dt


from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart
from .disk_shared import collect_disk_dataframe


class DiskChartCollector(BaseCollector):
    """Coletor para o módulo Uso de Disco (Gráficos)."""

    DEFAULT_TITLE = 'Uso de Disco (Gráficos)'

    def collect(self, all_hosts, period):
        df_disk, warning = collect_disk_dataframe(self.generator, self.module_config, all_hosts, period)
        opts = self.module_config.get('custom_options', {}) or {}
        show_summary = bool(opts.get('show_summary', True))
        top_n = int(opts.get('top_n') or 0)
        label_wrap = int(opts.get('label_wrap') or 48)
        show_values = bool(opts.get('show_values', False))
        rotate_x = bool(opts.get('rotate_x_labels', False))

        if df_disk.empty:
            warning = warning or 'Não foram encontrados dados de disco para o período selecionado.'
            img = None
            summary = None
        else:
            df_plot = df_disk.copy()
            if top_n and top_n > 0:
                df_plot = df_plot.sort_values(by='Avg', ascending=False).head(top_n)
            img = generate_multi_bar_chart(
                df_plot,
                'Uso de Disco (%)',
                'Uso de Disco (%)',
                ['#d1b3ff', '#a366ff', '#7a1aff'],
                label_wrap=label_wrap,
                show_values=show_values,
                rotate_x=rotate_x
            )
            summary = None
            if show_summary:
                try:
                    per_s = dt.datetime.fromtimestamp(int(period['start'])).strftime('%d/%m/%Y')
                    per_e = dt.datetime.fromtimestamp(int(period['end'])).strftime('%d/%m/%Y')
                    per_txt = f"{per_s} a {per_e}"
                except Exception:
                    per_txt = 'período selecionado'
                total_hosts = len(df_plot) if df_plot is not None else 0
                summary = (
                    f"Visualização do uso de disco por host (pior filesystem). "
                    f"Período: {per_txt}. Itens exibidos: {total_hosts}."
                )
                if top_n and top_n > 0:
                    summary += f" Top N aplicado: {top_n}."
        data = {
            'img': img,
            'summary_text': summary,
            'warning_text': warning
        }
        if not self.module_config.get('title'):
            self.module_config['title'] = self.DEFAULT_TITLE
        return self.render('disk_chart', data)

