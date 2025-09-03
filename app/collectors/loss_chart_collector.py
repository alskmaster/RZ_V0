from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart
import pandas as pd


class LossChartCollector(BaseCollector):
    """
    Perda de Pacotes (Gráficos): gráfico Min/Avg/Max com filtro por host.
    Opções: host_name_contains, top_n, cores.
    """
    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de Perda (gráficos)...")
        o = self.module_config.get('custom_options', {})
        host_contains = (o.get('host_name_contains') or '').strip()
        top_n = int(o.get('top_n') or 0)
        colors = [o.get('color_max') or '#ffdf80', o.get('color_avg') or '#ffc61a', o.get('color_min') or '#cc9900']
        label_wrap = int(o.get('label_wrap') or 45)

        cache_key = 'latency_loss_data'
        if cache_key not in self.generator.cached_data:
            data, error = self.generator.shared_collect_latency_and_loss(all_hosts, period)
            if error:
                return self.render('loss_chart', {'img': None})
            self.generator.cached_data[cache_key] = data
        df = self.generator.cached_data[cache_key].get('df_loss', pd.DataFrame())
        if df.empty:
            return self.render('loss_chart', {'img': None})

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
        img = generate_multi_bar_chart(df, 'Perda de Pacotes Média (%)', 'Perda (%)', colors, label_wrap=label_wrap)
        return self.render('loss_chart', {'img': img})
