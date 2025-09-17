# app/collectors/disk_table_collector.py
import datetime as dt

import pandas as pd

from .base_collector import BaseCollector
from .disk_shared import collect_disk_dataframe


class DiskTableCollector(BaseCollector):
    """Coletor para o módulo Uso de Disco (Tabela)."""

    DEFAULT_TITLE = 'Uso de Disco (Tabela)'

    def collect(self, all_hosts, period):
        df_disk, warning = collect_disk_dataframe(self.generator, self.module_config, all_hosts, period)
        opts = self.module_config.get('custom_options', {}) or {}
        show_summary = bool(opts.get('show_summary', True))
        top_n = int(opts.get('top_n') or 0)
        decimals = int(opts.get('decimals') or 2)
        if decimals < 0:
            decimals = 0

        if df_disk.empty:
            warning = warning or 'Nao foram encontrados dados de disco para o periodo selecionado.'
            table_html = None
            summary = None
        else:
            df_table = df_disk.copy()
            if top_n and top_n > 0:
                df_table = df_table.sort_values(by='Avg', ascending=False).head(top_n)
            df_fmt = df_table.rename(columns={'Host': 'Host', 'Filesystem': 'Filesystem', 'Min': 'Mínimo (%)', 'Avg': 'Médio (%)', 'Max': 'Máximo (%)'})
            for column in ['Mínimo (%)', 'Médio (%)', 'Máximo (%)']:
                df_fmt[column] = pd.to_numeric(df_fmt[column], errors='coerce').map(
                    lambda value: f"{value:.{decimals}f}" if pd.notna(value) else ''
                )
            table_html = df_fmt.to_html(classes='table table-sm', index=False, escape=False)
            summary = None
            if show_summary:
                try:
                    per_s = dt.datetime.fromtimestamp(int(period['start'])).strftime('%d/%m/%Y')
                    per_e = dt.datetime.fromtimestamp(int(period['end'])).strftime('%d/%m/%Y')
                    per_txt = f"{per_s} a {per_e}"
                except Exception:
                    per_txt = 'periodo selecionado'
                total_rows = len(df_fmt)
                summary = (
                    f"Tabela de uso de disco por host (pior filesystem). periodo: {per_txt}. Linhas exibidas: {total_rows}."
                )
                if top_n and top_n > 0:
                    summary += f" Top N aplicado: {top_n}."

        data = {
            'table_html': table_html,
            'summary_text': summary,
            'warning_text': warning
        }
        if not self.module_config.get('title'):
            self.module_config['title'] = self.DEFAULT_TITLE
        return self.render('disk_table', data)

