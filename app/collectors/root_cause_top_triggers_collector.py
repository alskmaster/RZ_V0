from .base_collector import BaseCollector
from flask import current_app
import datetime as dt
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64


class RootCauseTopTriggersCollector(BaseCollector):
    """
    Analise de Causa-Raiz (Top N Gatilhos) - ASCII only

    - Conta ativacoes de PROBLEM por triggerid e soma a duracao correlacionada (OK - PROBLEM).
    - Respeita cliente/periodo do gerador; possui sub-filtro opcional.

    custom_options:
      - top_n: int (default 5)
      - severities: [info, warning, average, high, disaster] (default todas)
      - period_sub_filter: full_month | last_24h | last_7d (default full_month)
      - host_name_contains: filtro textual por host visivel (opcional)
      - sort_by: 'count' | 'downtime' (default 'count')
      - show_table: bool (default True)
    """

    _SEVERITY_FILTER_MAP = {
        'info': '1', 'warning': '2', 'average': '3', 'high': '4', 'disaster': '5', 'not_classified': '0'
    }

    def _apply_period_subfilter(self, period, sub):
        start, end = period['start'], period['end']
        try:
            now = int(dt.datetime.now().timestamp())
        except Exception:
            from time import time as _t
            now = int(_t())
        if sub == 'last_24h':
            end = now
            start = end - 24 * 3600
        elif sub == 'last_7d':
            end = now
            start = end - 7 * 24 * 3600
        return {'start': int(start), 'end': int(end)}

    def _fmt_seconds(self, total_seconds):
        try:
            total_seconds = int(total_seconds or 0)
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            return "00:00:00"

    def _img_bars(self, df):
        if df is None or df.empty:
            return None
        names = df['Trigger'].tolist()
        counts = df['Ocorrencias'].astype(int).tolist()
        dts = df['Downtime_s'].astype(int).tolist()

        x = np.arange(len(names))
        width = 0.42
        fig, ax1 = plt.subplots(figsize=(12, 5))
        ax2 = ax1.twinx()
        b1 = ax1.bar(x - width/2, counts, width, color='#1e88e5', label='Ocorrencias')
        b2 = ax2.bar(x + width/2, np.array(dts)/3600.0, width, color='#e53935', label='Downtime (h)')
        ax1.set_xlabel('Trigger')
        ax1.set_ylabel('Ocorrencias')
        ax2.set_ylabel('Downtime (horas)')
        ax1.set_xticks(x)
        ax1.set_xticklabels(names, rotation=45, ha='right')
        ax1.grid(True, axis='y', linestyle='--', alpha=0.3)
        ax1.legend([b1, b2], ['Ocorrencias', 'Downtime (h)'], loc='upper right')
        fig.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {}) or {}
        top_n = int(o.get('top_n') or 5)
        severities = o.get('severities', ['info', 'warning', 'average', 'high', 'disaster'])
        ids = [self._SEVERITY_FILTER_MAP[s] for s in severities if s in self._SEVERITY_FILTER_MAP]
        sort_by = (o.get('sort_by') or 'count').lower()
        show_table = o.get('show_table', True)
        host_contains = (o.get('host_name_contains') or '').strip()
        period = self._apply_period_subfilter(period, o.get('period_sub_filter', 'full_month'))
        try:
            _s = dt.datetime.fromtimestamp(int(period['start'])).strftime('%d-%m-%Y')
            _e = dt.datetime.fromtimestamp(int(period['end'])).strftime('%d-%m-%Y')
            self._update_status(f"root_cause_top_triggers | periodo efetivo {_s} - {_e}")
        except Exception:
            pass

        if host_contains:
            try:
                all_hosts = [h for h in (all_hosts or []) if host_contains.lower() in str(h.get('nome_visivel','')).lower()]
            except Exception:
                pass
        if not all_hosts:
            return self.render('root_cause_top_triggers', {
                'error': 'Nenhum host disponivel para analise no periodo.',
                'chart_b64': None,
                'rows': [],
            })

        all_host_ids = [h['hostid'] for h in all_hosts]
        events = self.generator.obter_eventos_wrapper(all_host_ids, period, 'hostids')
        if events is None:
            return self.render('root_cause_top_triggers', {
                'error': 'Falha ao coletar eventos.', 'chart_b64': None, 'rows': []
            })

        df = pd.DataFrame(events)
        if df.empty:
            return self.render('root_cause_top_triggers', {'chart_b64': None, 'rows': []})
        for c in ('source', 'object', 'value', 'severity'):
            if c in df.columns:
                df[c] = df[c].astype(str)
        df = df[(df['source'] == '0') & (df['object'] == '0')]
        problems = df[df['value'] == '1']
        if ids:
            problems = problems[problems['severity'].astype(str).isin(ids)]
        if problems.empty:
            return self.render('root_cause_top_triggers', {'chart_b64': None, 'rows': []})

        try:
            corr = self.generator._correlate_problems(problems.to_dict('records'), df.to_dict('records'), period)
        except Exception:
            corr = []
        if not corr:
            return self.render('root_cause_top_triggers', {'chart_b64': None, 'rows': []})

        rows = {}
        name_map = {}
        try:
            for _, r in problems.iterrows():
                tid = str(r.get('objectid') or r.get('triggerid'))
                nm = str(r.get('name') or f"Trigger {tid}")
                name_map.setdefault(tid, {})
                name_map[tid][nm] = name_map[tid].get(nm, 0) + 1
        except Exception:
            pass

        for it in (corr or []):
            try:
                tid = str(it.get('triggerid'))
                d = max(0, int(it.get('end', 0)) - int(it.get('start', 0)))
                if tid not in rows:
                    nm = f"Trigger {tid}"
                    if tid in name_map:
                        nm = sorted(name_map[tid].items(), key=lambda kv: kv[1], reverse=True)[0][0]
                    rows[tid] = {'Trigger': nm, 'Ocorrencias': 0, 'Downtime_s': 0}
                rows[tid]['Ocorrencias'] += 1
                rows[tid]['Downtime_s'] += d
            except Exception:
                continue

        if not rows:
            return self.render('root_cause_top_triggers', {'chart_b64': None, 'rows': []})
        out = pd.DataFrame(list(rows.values()))
        if sort_by == 'downtime':
            out = out.sort_values(by=['Downtime_s', 'Ocorrencias'], ascending=[False, False])
        else:
            out = out.sort_values(by=['Ocorrencias', 'Downtime_s'], ascending=[False, False])
        out = out.head(max(1, top_n))
        out['Downtime_str'] = out['Downtime_s'].apply(self._fmt_seconds)

        chart_b64 = self._img_bars(out)
        return self.render('root_cause_top_triggers', {
            'chart_b64': chart_b64,
            'rows': out.to_dict('records') if show_table else [],
            'show_table': bool(show_table),
        })

