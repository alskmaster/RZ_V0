from .base_collector import BaseCollector
from app.collectors.robust_metric_engine import RobustMetricEngine
import pandas as pd


class CpuTableCollector(BaseCollector):
    """
    CPU (Tabela): apresenta Min/Avg/Max por host com filtro "host contém".
    Opções: host_name_contains, sort_by, sort_asc, top_n, decimals.
    """
    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de CPU (tabela)...")

        opts = self.module_config.get('custom_options', {})
        host_contains = (opts.get('host_name_contains') or '').strip()
        sort_by = (opts.get('sort_by') or 'Avg')
        sort_asc = bool(opts.get('sort_asc', False))
        top_n = int(opts.get('top_n') or 0)
        decimals = int(opts.get('decimals') or 2)

        engine = RobustMetricEngine(self.generator)
        df = engine.collect_cpu_or_mem('cpu', all_hosts, period)
        if df is None or df.empty:
            return "<p><i>Sem dados de CPU para o período selecionado.</i></p>"

        if host_contains:
            try:
                df = df[df['Host'].astype(str).str.contains(host_contains, case=False, na=False)]
            except Exception:
                pass
        if sort_by in df.columns:
            try:
                df = df.sort_values(by=sort_by, ascending=sort_asc)
            except Exception:
                pass
        if top_n and top_n > 0:
            df = df.head(top_n)

        try:
            df_fmt = df.copy()
            for c in ['Min', 'Avg', 'Max']:
                if c in df_fmt.columns:
                    df_fmt[c] = pd.to_numeric(df_fmt[c], errors='coerce').map(lambda v: f"{v:.{decimals}f}" if pd.notna(v) else '')
        except Exception:
            df_fmt = df

        html = df_fmt.to_html(classes='table', index=False, escape=False)
        return self.render('cpu_table', {'table_html': html})

