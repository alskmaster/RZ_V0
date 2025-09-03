from .base_collector import BaseCollector
from flask import current_app
import pandas as pd
from app.charting import generate_chart


class UptimeChartCollector(BaseCollector):
    """
    Uptime (Gráficos): barras horizontais por host com dias de uptime estimados
    no fim do período.

    custom_options:
      - top_n: int (0 = todos)
      - order: 'asc'|'desc' (default 'desc')
      - color: str hex (default '#4e79a7')
      - target_days: float (opcional) — destaca abaixo da meta
      - below_color: str hex (default '#e55353')
      - label_wrap: int (default 45)
      - dynamic_height: bool (default true)
      - height_per_bar: float (default 0.35)
      - show_values: bool (default true)
      - grid: bool (default true)
    """

    def _collect_days(self, all_hosts, period):
        # Reaproveita a coleta da tabela via import local para evitar duplicação
        from .uptime_table_collector import UptimeTableCollector
        tmp = UptimeTableCollector(self.generator, self.module_config)
        df = tmp._collect_raw(all_hosts, period)
        if df is None or df.empty:
            return pd.DataFrame(columns=['Host','Days'])
        return df[['Host','Days']]

    def collect(self, all_hosts, period):
        self._update_status("Coletando Uptime (gráficos)...")
        opts = self.module_config.get('custom_options', {})
        top_n = int(opts.get('top_n') or 0)
        order = (opts.get('order') or 'desc').lower()
        color = opts.get('color') or '#4e79a7'
        target_days = opts.get('target_days')
        below_color = opts.get('below_color') or '#e55353'
        label_wrap = int(opts.get('label_wrap') or 45)
        dynamic_height = bool(opts.get('dynamic_height', True))
        height_per_bar = float(opts.get('height_per_bar') or 0.35)
        show_values = bool(opts.get('show_values', True))
        grid = bool(opts.get('grid', True))

        df = self._collect_days(all_hosts, period)
        if df is None or df.empty:
            return "<p><i>Sem dados de uptime para o período selecionado.</i></p>"

        try:
            df['Days'] = pd.to_numeric(df['Days'], errors='coerce')
            df = df.dropna(subset=['Days'])
        except Exception:
            pass

        if top_n and top_n > 0:
            # maiores uptimes primeiro por padrão
            df = df.nlargest(top_n, 'Days')

        # Ordenação final para o gráfico
        ascending = (order == 'asc')
        try:
            df = df.sort_values(by='Days', ascending=ascending)
        except Exception:
            pass

        img_b64 = generate_chart(
            df=df,
            x_col='Days',
            y_col='Host',
            title='Uptime por Host (em dias)',
            x_label='Dias de Uptime',
            chart_color=color,
            target_line=target_days,
            below_color=below_color,
            xlim=None,
            label_wrap=label_wrap,
            dynamic_height=dynamic_height,
            height_per_bar=height_per_bar,
            show_values=show_values,
            grid=grid,
        )
        if not img_b64:
            return "<p><i>Não foi possível gerar o gráfico de uptime.</i></p>"
        return self.render('uptime_chart', {'img_b64': img_b64})

