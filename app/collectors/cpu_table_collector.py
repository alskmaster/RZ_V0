from .base_collector import BaseCollector
from app.collectors.robust_metric_engine import RobustMetricEngine
import pandas as pd
import datetime as dt


class CpuTableCollector(BaseCollector):
    """
    CPU (Tabela): apresenta Min/Avg/Max por host com filtros e resumo.

    Opções suportadas (custom_options):
      - host_name_contains: texto de inclusão
      - exclude_hosts_contains: CSV de exclusões
      - sort_by: Avg|Max|Min
      - sort_asc: bool (True=ascendente)
      - top_n: int (0=todos)
      - decimals: int (padrão 2)
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

    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de CPU (tabela)...")

        opts = self.module_config.get('custom_options', {}) or {}
        host_contains = (opts.get('host_name_contains') or '').strip()
        exclude_raw = (opts.get('exclude_hosts_contains') or '')
        exclude_terms = [t.strip().lower() for t in exclude_raw.split(',') if t.strip()]
        sort_by = (opts.get('sort_by') or 'Avg')
        sort_asc = bool(opts.get('sort_asc', False))
        top_n = int(opts.get('top_n') or 0)
        decimals = int(opts.get('decimals') or 2)
        show_summary = bool(opts.get('show_summary', True))
        period = self._apply_period_subfilter(period, opts.get('period_sub_filter', 'full_month'))

        engine = RobustMetricEngine(self.generator)
        df = engine.collect_cpu_or_mem('cpu', all_hosts, period)
        if df is None or df.empty:
            return self.render('cpu_table', {'table_html': '<p><i>Sem dados de CPU para o período selecionado.</i></p>', 'summary_text': None})

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

        summary = None
        if show_summary:
            try:
                per_s = dt.datetime.fromtimestamp(int(period['start'])).strftime('%d/%m/%Y')
                per_e = dt.datetime.fromtimestamp(int(period['end'])).strftime('%d/%m/%Y')
                per_txt = f"{per_s} a {per_e}"
            except Exception:
                per_txt = "período selecionado"
            ord_txt = f"ordenado por {sort_by} ({'asc' if sort_asc else 'desc'})"
            items = len(df_fmt) if df_fmt is not None else 0
            summary = f"Tabela de uso de CPU por host (Min/Avg/Max), {ord_txt}. Período: {per_txt}. Itens exibidos: {items}."

        return self.render('cpu_table', {'table_html': html, 'summary_text': summary})

