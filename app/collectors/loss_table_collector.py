from .base_collector import BaseCollector
import pandas as pd


class LossTableCollector(BaseCollector):
    """
    Perda de Pacotes (Tabela): apresenta Min/Avg/Max por host com filtro "host contém".
    Opções: host_name_contains, sort_by, sort_asc, top_n, decimals.
    """
    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de Perda (tabela)...")

        opts = self.module_config.get('custom_options', {})
        host_contains = (opts.get('host_name_contains') or '').strip()
        sort_by = (opts.get('sort_by') or 'Avg')
        sort_asc = bool(opts.get('sort_asc', False))
        top_n = int(opts.get('top_n') or 0)
        decimals = int(opts.get('decimals') or 2)

        cache_key = 'latency_loss_data'
        if cache_key not in self.generator.cached_data:
            data, error = self.generator.shared_collect_latency_and_loss(all_hosts, period)
            if error:
                return f"<p><i>{error}</i></p>"
            self.generator.cached_data[cache_key] = data
        df = self.generator.cached_data[cache_key].get('df_loss') or pd.DataFrame()
        if df.empty:
            return "<p><i>Sem dados de perda de pacotes.</i></p>"

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
                df_fmt[c] = pd.to_numeric(df_fmt[c], errors='coerce').map(lambda v: f"{v:.{decimals}f}" if pd.notna(v) else '')
        except Exception:
            df_fmt = df
        html = df_fmt.to_html(classes='table', index=False, escape=False)
        return self.render('loss_table', {'table_html': html})

