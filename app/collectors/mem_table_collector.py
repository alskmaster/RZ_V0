from .base_collector import BaseCollector
from app.collectors.robust_metric_engine import RobustMetricEngine
from flask import current_app
import pandas as pd


class MemTableCollector(BaseCollector):
    """
    Memória (Tabela): apresenta Min/Avg/Max por host com filtro "host contém".
    Opções (custom_options):
      - host_name_contains: str
      - sort_by: 'Avg'|'Max'|'Min' (default 'Avg')
      - sort_asc: bool (default False)
      - top_n: int (0 = todos)
      - decimals: int (default 2)
    """

    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de Memória (tabela)...")

        opts = self.module_config.get('custom_options', {})
        host_contains = (opts.get('host_name_contains') or '').strip()
        sort_by = (opts.get('sort_by') or 'Avg')
        sort_asc = bool(opts.get('sort_asc', False))
        top_n = int(opts.get('top_n') or 0)
        decimals = int(opts.get('decimals') or 2)

        engine = RobustMetricEngine(self.generator)
        df = engine.collect_cpu_or_mem('memory', all_hosts, period)
        if df is None or df.empty:
            return "<p><i>Sem dados de memória para o período selecionado.</i></p>"

        # filtro por host
        if host_contains:
            try:
                df = df[df['Host'].astype(str).str.contains(host_contains, case=False, na=False)]
            except Exception:
                pass

        # ordenação
        if sort_by in df.columns:
            try:
                df = df.sort_values(by=sort_by, ascending=sort_asc)
            except Exception:
                pass

        # top N
        if top_n and top_n > 0:
            df = df.head(top_n)

        # formatação
        try:
            df_fmt = df.copy()
            for c in ['Min', 'Avg', 'Max']:
                if c in df_fmt.columns:
                    df_fmt[c] = pd.to_numeric(df_fmt[c], errors='coerce').map(lambda v: f"{v:.{decimals}f}" if pd.notna(v) else '')
        except Exception:
            df_fmt = df

        html = df_fmt.to_html(classes='table', index=False, escape=False)
        return self.render('mem_table', {'table_html': html})

