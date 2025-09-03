from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart
import pandas as pd


class LatencyChartCollector(BaseCollector):
    """
    Latência (Gráficos): gráfico Min/Avg/Max com filtro por host.
    Opções: host_name_contains, top_n, cores (min/avg/max).
    """
    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de Latência (gráficos)...")
        o = self.module_config.get('custom_options', {})
        host_contains = (o.get('host_name_contains') or '').strip()
        top_n = int(o.get('top_n') or 0)
        colors = [o.get('color_max') or '#ffb3b3', o.get('color_avg') or '#ff6666', o.get('color_min') or '#cc0000']

        cache_key = 'latency_loss_data'
        if cache_key not in self.generator.cached_data:
            data, error = self.generator.shared_collect_latency_and_loss(all_hosts, period)
            if error:
                return self.render('latency_chart', {'img': None})
            self.generator.cached_data[cache_key] = data
        df = self.generator.cached_data[cache_key].get('df_lat', pd.DataFrame())
        if df.empty:
            return self.render('latency_chart', {'img': None})

        if host_contains:
            try:
                df = df[df['Host'].astype(str).str.contains(host_contains, case=False, na=False)]
            except Exception:
                pass
        if top_n and top_n > 0:
            try:
                df = df.sort_values(by='Avg', ascending=False).head(top_n)
            except Exception:
                df = df.head(top_n)
        img = generate_multi_bar_chart(df, 'Latência Média (ms)', 'Latência (ms)', colors)
        return self.render('latency_chart', {'img': img})
