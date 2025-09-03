from .base_collector import BaseCollector
from app.collectors.robust_metric_engine import RobustMetricEngine
from app.charting import generate_multi_bar_chart


class CpuChartCollector(BaseCollector):
    """
    CPU (Gráficos): gráfico horizontal Min/Avg/Max com filtro por host.
    Opções (custom_options): host_name_contains, top_n, cores e label_wrap.
    """
    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de CPU (gráficos)...")

        o = self.module_config.get('custom_options', {})
        host_contains = (o.get('host_name_contains') or '').strip()
        top_n = int(o.get('top_n') or 0)
        colors = [o.get('color_max') or '#ff9999', o.get('color_avg') or '#ff4d4d', o.get('color_min') or '#cc0000']
        label_wrap = int(o.get('label_wrap') or 45)

        engine = RobustMetricEngine(self.generator)
        df = engine.collect_cpu_or_mem('cpu', all_hosts, period)
        if df is None or df.empty:
            return self.render('cpu_chart', {'img': None})

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

        img = generate_multi_bar_chart(df, 'Ocupação de CPU (%)', 'Uso de CPU (%)', colors, label_wrap=label_wrap)
        return self.render('cpu_chart', {'img': img})

