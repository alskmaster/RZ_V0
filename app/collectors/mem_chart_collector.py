from .base_collector import BaseCollector
from app.collectors.robust_metric_engine import RobustMetricEngine
from app.charting import generate_multi_bar_chart
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import datetime as dt
import textwrap


class MemChartCollector(BaseCollector):
    """
    Memória (Gráficos): Min/Avg/Max com filtros, período e tipos (Barras/Pizza).

    Opções (custom_options):
      - host_name_contains / exclude_hosts_contains (CSV)
      - top_n (0=todos)
      - chart_type: 'bar' | 'pie' (default 'bar')
      - rotate_x_labels: bool (barras)
      - color_max/color_avg/color_min
      - show_values: bool
      - label_wrap: int (default 48)
      - period_sub_filter: full_month | last_24h | last_7d
      - show_summary: bool
    """

    def _apply_period_subfilter(self, period, sub):
        start, end = period.get('start'), period.get('end')
        try:
            now = int(dt.datetime.now().timestamp())
        except Exception:
            from time import time as _t
            now = int(_t())
        sub = (sub or 'full_month')
        if sub == 'last_24h':
            end = now; start = end - 24*3600
        elif sub == 'last_7d':
            end = now; start = end - 7*24*3600
        return {'start': int(start), 'end': int(end)}

    def _pie(self, df, label_wrap=48, show_values=True):
        try:
            if 'Avg' not in df.columns:
                return None
            labels = df['Host'].astype(str).tolist()
            wrapped = ['\n'.join(textwrap.wrap(l, width=int(label_wrap) if label_wrap else 48)) for l in labels]
            sizes = pd.to_numeric(df['Avg'], errors='coerce').fillna(0).tolist()
            if not any(sizes):
                return None
            plt.style.use('seaborn-v0_8-whitegrid')
            fig, ax = plt.subplots(figsize=(9,6))
            autopct = '%1.1f%%' if show_values else None
            ax.pie(sizes, labels=wrapped, autopct=autopct, startangle=90, textprops={'fontsize': 9})
            ax.axis('equal')
            plt.tight_layout()
            buf = BytesIO(); plt.savefig(buf, format='png', dpi=150, transparent=True); plt.close(fig)
            return base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception:
            return None

    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de Memória (gráficos)...")
        o = self.module_config.get('custom_options', {}) or {}

        host_contains = (o.get('host_name_contains') or '').strip()
        exclude_raw = (o.get('exclude_hosts_contains') or '')
        exclude_terms = [t.strip().lower() for t in exclude_raw.split(',') if t.strip()]
        top_n = int(o.get('top_n') or 0)
        chart_type = (o.get('chart_type') or 'bar').lower()
        rotate_x = bool(o.get('rotate_x_labels'))
        colors = [o.get('color_max') or '#66b3ff', o.get('color_avg') or '#3385ff', o.get('color_min') or '#0047b3']
        show_values = bool(o.get('show_values', False))
        label_wrap = int(o.get('label_wrap') or 48)
        show_summary = bool(o.get('show_summary', True))
        period = self._apply_period_subfilter(period, o.get('period_sub_filter', 'full_month'))

        engine = RobustMetricEngine(self.generator)
        df = engine.collect_cpu_or_mem('memory', all_hosts, period)
        if df is None or df.empty:
            return self.render('mem_chart', {'img': None, 'summary_text': None})

        if host_contains:
            try:
                df = df[df['Host'].astype(str).str.contains(host_contains, case=False, na=False)]
            except Exception:
                pass
        if exclude_terms:
            try:
                mask = ~df['Host'].astype(str).str.lower().apply(lambda h: any(t in h for t in exclude_terms))
                df = df[mask]
            except Exception:
                pass
        if top_n and top_n > 0:
            try:
                df = df.sort_values(by='Avg', ascending=False).head(top_n)
            except Exception:
                df = df.head(top_n)

        if chart_type == 'pie':
            img = self._pie(df, label_wrap=label_wrap, show_values=show_values)
        else:
            img = generate_multi_bar_chart(
                df, 'Uso de Memória (%)', 'Uso de Memória (%)', colors,
                label_wrap=label_wrap, show_values=show_values, rotate_x=rotate_x
            )

        summary = None
        if show_summary:
            try:
                per_s = dt.datetime.fromtimestamp(int(period['start'])).strftime('%d/%m/%Y')
                per_e = dt.datetime.fromtimestamp(int(period['end'])).strftime('%d/%m/%Y')
                per_txt = f"{per_s} a {per_e}"
            except Exception:
                per_txt = 'período selecionado'
            tipo = 'Pizza' if chart_type == 'pie' else 'Barras'
            total_hosts = len(df) if df is not None else 0
            summary = (
                f"Visualização de uso de Memória por host em {tipo}. "
                f"Considera estatísticas de Mínimo, Médio e Máximo. "
                f"Período: {per_txt}. Itens exibidos: {total_hosts}."
            )

        return self.render('mem_chart', {'img': img, 'summary_text': summary})

