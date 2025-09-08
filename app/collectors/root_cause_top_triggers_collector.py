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
      - top_n: int (default 5) [fallback]
      - top_n_table: int (linhas da tabela; fallback para top_n)
      - top_n_chart: int (series para grafico; fallback para top_n)
      - severities: [info, warning, average, high, disaster] (default todas)
      - period_sub_filter: full_month | last_24h | last_7d (default full_month)
      - host_name_contains: filtro textual por host visivel (opcional)
      - sort_by: 'count' | 'downtime' (default 'count')
      - show_table: bool (default True)
      - show_chart: bool (default True)
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

    def _img_bars(self, df, max_label_len=48, show_values=True):
        if df is None or df.empty:
            return None
        names = [ (str(x)[:max_label_len-1] + '...') if isinstance(x,str) and len(str(x))>max_label_len else str(x) for x in df['Trigger'].tolist() ]
        counts = df['Ocorrencias'].astype(int).tolist()
        hours = (df['Downtime_s'].astype(int) / 3600.0).tolist()

        n = len(names)
        height = max(4.0, 0.7 * n + 1.2)
        fig, ax1 = plt.subplots(figsize=(12, height))
        ax2 = ax1.twiny()
        y = np.arange(n)
        h = 0.35
        b1 = ax1.barh(y - h/2, counts, height=h, color='#1e88e5', label='Ocorrencias')
        b2 = ax2.barh(y + h/2, hours, height=h, color='#e53935', label='Downtime (h)')
        ax1.set_yticks(y)
        ax1.set_yticklabels(names)
        ax1.invert_yaxis()
        ax1.set_xlabel('Ocorrencias')
        ax2.set_xlabel('Downtime (horas)')
        ax1.grid(True, axis='x', linestyle='--', alpha=0.3)
        if show_values:
            for rect in b1:
                w = rect.get_width()
                ax1.text(w + max(0.02*max(counts+[1]), 0.5), rect.get_y()+rect.get_height()/2, f"{int(w)}", va='center', fontsize=8, color='#1e88e5')
            for rect in b2:
                w = rect.get_width()
                ax2.text(w + max(0.02*max(hours+[0.1]), 0.1), rect.get_y()+rect.get_height()/2, f"{w:.1f}h", va='center', fontsize=8, color='#e53935')
        ax1.legend([b1, b2], ['Ocorrencias', 'Downtime (h)'], loc='lower right', fontsize=9)
        fig.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {}) or {}
        top_n_common = int(o.get('top_n') or 5)
        top_n_table = int(o.get('top_n_table') or top_n_common)
        top_n_chart = int(o.get('top_n_chart') or top_n_common)
        severities = o.get('severities', ['info', 'warning', 'average', 'high', 'disaster'])
        ids = [self._SEVERITY_FILTER_MAP[s] for s in severities if s in self._SEVERITY_FILTER_MAP]
        sort_by = (o.get('sort_by') or 'count').lower()
        show_table = o.get('show_table', True)
        show_chart = o.get('show_chart', True)
        host_contains = (o.get('host_name_contains') or '').strip()
        trigger_contains = (o.get('trigger_name_contains') or '').strip()
        exclude_triggers_contains_raw = (o.get('exclude_triggers_contains') or '').strip()
        exclude_hosts_contains_raw = (o.get('exclude_hosts_contains') or '').strip()
        exclude_terms = [s.strip().lower() for s in exclude_hosts_contains_raw.split(',') if s and s.strip()]
        def _to_bool(v):
            try:
                if isinstance(v, bool):
                    return v
                return str(v).strip().lower() in ('1','true','yes','on')
            except Exception:
                return False
        sort_asc = _to_bool(o.get('sort_asc', False))
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
        # Excluir hosts por substrings (lista separada por virgula)
        if exclude_terms:
            try:
                def _should_exclude(h):
                    name = str(h.get('nome_visivel','')).lower()
                    return any(term in name for term in exclude_terms)
                all_hosts = [h for h in (all_hosts or []) if not _should_exclude(h)]
            except Exception:
                pass
        try:
            self._update_status(
                f"root_cause_top_triggers | filtros: host_contains='{host_contains}', trig_contains='{trigger_contains}', excl_hosts={exclude_terms}, excl_triggers_raw='{exclude_triggers_contains_raw}', sevs={severities}, sort_by={sort_by}, sort_asc={sort_asc}, top_table={top_n_table}, top_chart={top_n_chart}"
            )
        except Exception:
            pass
        if not all_hosts:
            return self.render('root_cause_top_triggers', {
                'error': 'Nenhum host disponivel para analise no periodo.',
                'chart_b64': None,
                'rows': [],
                'period': period,
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
        try:
            self._update_status(f"root_cause_top_triggers | correlacoes: {len(corr) if corr else 0}")
        except Exception:
            pass
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
            out = out.sort_values(by=['Downtime_s', 'Ocorrencias'], ascending=[sort_asc, sort_asc])
        else:
            out = out.sort_values(by=['Ocorrencias', 'Downtime_s'], ascending=[sort_asc, sort_asc])
        # Aplicar filtros por nome de Trigger (include/exclude)
        try:
            if trigger_contains:
                out = out[out['Trigger'].astype(str).str.lower().str.contains(trigger_contains.lower(), na=False)]
            excl_terms_tr = [s.strip().lower() for s in exclude_triggers_contains_raw.split(',') if s and s.strip()]
            if excl_terms_tr:
                out = out[~out['Trigger'].astype(str).str.lower().apply(lambda nm: any(t in nm for t in excl_terms_tr))]
        except Exception:
            pass
        out['Downtime_str'] = out['Downtime_s'].apply(self._fmt_seconds)

        # Top N separado para tabela e grafico (com fallback)
        # Regra: se N <= 0, exibir tudo (sem limite)
        def _limit(df, n):
            try:
                n = int(n)
            except Exception:
                return df
            if n <= 0:
                return df
            return df.head(n)
        out_table = _limit(out, top_n_table)
        out_chart = _limit(out, top_n_chart)
        # Campo para tooltip completo na tabela
        try:
            out_table = out_table.copy()
            out_table['TriggerFull'] = out_table['Trigger']
        except Exception:
            pass

        chart_b64 = None
        if bool(show_chart):
            chart_b64 = self._img_bars(
                out_chart,
                max_label_len=int(o.get('max_label_len') or 48),
                show_values=bool(o.get('show_values', True))
            )
        try:
            self._update_status(f"root_cause_top_triggers | linhas tabela={len(out_table)}, series grafico={len(out_chart)}")
        except Exception:
            pass
        return self.render('root_cause_top_triggers', {
            'chart_b64': chart_b64,
            'rows': out_table.to_dict('records') if show_table else [],
            'show_table': bool(show_table),
            'period': period,
        })




