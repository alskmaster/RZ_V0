from .base_collector import BaseCollector
from app.collectors.robust_metric_engine import RobustMetricEngine
from app.charting import generate_multi_bar_chart
import pandas as pd


class MemChartCollector(BaseCollector):
    """
    Memória (Gráficos): gráfico horizontal Min/Avg/Max com opções visuais.
    Opções (custom_options):
      - host_name_contains: str
      - top_n: int (0 = todos)
      - color_min: str (hex) default '#66b3ff'
      - color_avg: str (hex) default '#3385ff'
      - color_max: str (hex) default '#0047b3'
    """

    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de Memória (gráficos)...")
        o = self.module_config.get('custom_options', {})
        host_contains = (o.get('host_name_contains') or '').strip()
        top_n = int(o.get('top_n') or 0)
        colors = [o.get('color_max') or '#66b3ff', o.get('color_avg') or '#3385ff', o.get('color_min') or '#0047b3']
        label_wrap = int(o.get('label_wrap') or 45)

        engine = RobustMetricEngine(self.generator)
        df = engine.collect_cpu_or_mem('memory', all_hosts, period)
        if df is None or df.empty:
            return self.render('mem_chart', {'img': None})

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

        img = generate_multi_bar_chart(df, 'Uso de Memória (%)', 'Uso de Memória (%)', colors, label_wrap=label_wrap)
        return self.render('mem_chart', {'img': img})
