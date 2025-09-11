from .base_collector import BaseCollector
import datetime as dt
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64


class MTTRCollector(BaseCollector):
    """
    Modulo MTTR (ASCII only)
    - Calcula MTTR e MTTD por severidade usando eventos PROBLEM/OK e reconhecimentos.
    - MTTD aqui = tempo medio ate primeiro reconhecimento (quando houver), senao ignora.
    custom_options:
      - severities: lista (default: info..disaster)
      - host_name_contains: filtro textual
      - period_sub_filter: full_month | last_24h | last_7d
      - only_acknowledged: bool (default False)
    """

    _SEVERITY_MAP = {
        '0': 'Nao Classificado', '1': 'Informacao', '2': 'Atencao', '3': 'Media', '4': 'Alta', '5': 'Desastre'
    }
    _SEVERITY_FILTER_MAP = {
        'info': '1', 'warning': '2', 'average': '3', 'high': '4', 'disaster': '5', 'not_classified': '0'
    }

    def _apply_period_subfilter(self, period, sub):
        start, end = period['start'], period['end']
        now = int(dt.datetime.now().timestamp())
        if sub == 'last_24h':
            end = now; start = end - 24*3600
        elif sub == 'last_7d':
            end = now; start = end - 7*24*3600
        return {'start': int(start), 'end': int(end)}

    def _fmt_seconds(self, s):
        try:
            s = int(max(0, s)); h=s//3600; m=(s%3600)//60; sec=s%60
            return f"{h:02d}:{m:02d}:{sec:02d}"
        except Exception:
            return "00:00:00"

    def _bars(self, labels, mttr_vals, mttd_vals):
        if not labels:
            return None
        x = np.arange(len(labels)); w = 0.35
        fig, ax = plt.subplots(figsize=(10, max(3.5, 0.5*len(labels)+2)))
        ax.barh(x - w/2, np.array(mttr_vals)/3600.0, height=w, color='#1e88e5', label='MTTR (h)')
        ax.barh(x + w/2, np.array(mttd_vals)/3600.0, height=w, color='#e53935', label='MTTD (h)')
        ax.set_yticks(x)
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.set_xlabel('Horas')
        ax.grid(True, axis='x', linestyle='--', alpha=0.3)
        ax.legend(loc='lower right')
        fig.tight_layout()
        buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight'); plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {}) or {}
        sevs = o.get('severities', ['info','warning','average','high','disaster'])
        ids = [self._SEVERITY_FILTER_MAP[s] for s in sevs if s in self._SEVERITY_FILTER_MAP]
        # ACK tri-state (mantém compat com only_acknowledged)
        ack_filter = (o.get('ack_filter') or ('only_acked' if o.get('only_acknowledged') else 'all')).lower()
        host_contains = (o.get('host_name_contains') or '').strip()
        excl_hosts_raw = (o.get('exclude_hosts_contains') or '')
        excl_host_terms = [s.strip().lower() for s in str(excl_hosts_raw).split(',') if s.strip()]
        trig_contains = (o.get('trigger_name_contains') or '').strip()
        excl_trig_raw = (o.get('exclude_triggers_contains') or '')
        excl_trig_terms = [s.strip().lower() for s in str(excl_trig_raw).split(',') if s.strip()]
        tags_inc = (o.get('tags_include') or '').strip()
        tags_exc = (o.get('tags_exclude') or '').strip()
        period = self._apply_period_subfilter(period, o.get('period_sub_filter', 'full_month'))

        if host_contains:
            try:
                all_hosts = [h for h in (all_hosts or []) if host_contains.lower() in str(h.get('nome_visivel','')).lower()]
            except Exception:
                pass
        if excl_host_terms:
            try:
                def _hex(name):
                    nm = str(name or '').lower()
                    return any(t in nm for t in excl_host_terms)
                all_hosts = [h for h in (all_hosts or []) if not _hex(h.get('nome_visivel'))]
            except Exception:
                pass
        if not all_hosts:
            return self.render('mttr', {'error': 'Nenhum host para o periodo informado.'})

        evs = self.generator.obter_eventos_wrapper([h['hostid'] for h in all_hosts], period, 'hostids')
        if evs is None:
            return self.render('mttr', {'error': 'Falha ao coletar eventos.'})

        df = pd.DataFrame(evs)
        if df.empty:
            return self.render('mttr', {'chart_b64': None, 'rows': []})
        for c in ('source','object','value','severity'):
            if c in df.columns: df[c]=df[c].astype(str)
        df = df[(df['source']=='0') & (df['object']=='0')]

        problems = df[df['value']=='1']
        if ids: problems = problems[problems['severity'].astype(str).isin(ids)]
        # Filtro ACK: all | only_acked | only_unacked
        if 'acknowledges' in problems.columns:
            if ack_filter == 'only_acked':
                problems = problems[problems['acknowledges'].apply(lambda a: isinstance(a,list) and len(a)>0)]
            elif ack_filter == 'only_unacked':
                problems = problems[~problems['acknowledges'].apply(lambda a: isinstance(a,list) and len(a)>0)]
        # Filtros por trigger name
        try:
            if trig_contains:
                problems = problems[problems.get('name').astype(str).str.lower().str.contains(trig_contains.lower(), na=False)]
            if excl_trig_terms:
                problems = problems[~problems.get('name').astype(str).str.lower().apply(lambda nm: any(t in nm for t in excl_trig_terms))]
        except Exception:
            pass
        # Filtros por tags quando disponíveis
        if ('tags' in problems.columns) and (tags_inc or tags_exc):
            inc = [t.strip().lower() for t in tags_inc.split(',') if t.strip()]
            exc = [t.strip().lower() for t in tags_exc.split(',') if t.strip()]
            def _norm_tags(tlist):
                try:
                    return [ (str((tt.get('tag') if isinstance(tt, dict) else '')) + ':' + str((tt.get('value') if isinstance(tt, dict) else ''))).lower() for tt in (tlist or []) if isinstance(tt, dict) ]
                except Exception:
                    return []
            try:
                _tcol = problems['tags'].apply(_norm_tags)
                if inc:
                    problems = problems[_tcol.apply(lambda lst: any(any(i in s for s in lst) for i in inc))]
                if exc:
                    problems = problems[~_tcol.apply(lambda lst: any(any(e in s for s in lst) for e in exc))]
            except Exception:
                pass
        if problems.empty:
            return self.render('mttr', {'chart_b64': None, 'rows': []})

        corr = self.generator._correlate_problems(problems.to_dict('records'), df.to_dict('records'), period) or []
        if not corr:
            return self.render('mttr', {'chart_b64': None, 'rows': []})

        mttr_map = {}; mttd_map = {}
        pidx = {}
        for _, r in problems.iterrows():
            tid = str(r.get('objectid') or r.get('triggerid'))
            key = (tid, int(r.get('clock',0)))
            sev = str(r.get('severity','0'))
            pidx[key] = {'sev': sev, 'acks': r.get('acknowledges')}
        for it in corr:
            tid = str(it.get('triggerid')); st=int(it.get('start',0)); en=int(it.get('end',0))
            info = pidx.get((tid, st))
            if not info: continue
            sev = info['sev']
            mttr_map.setdefault(sev, []).append(max(0, en-st))
            acks = info.get('acks') or []
            if isinstance(acks, list) and acks:
                try:
                    first_ack = min(int(a.get('clock', en)) for a in acks if isinstance(a, dict))
                    mttd_map.setdefault(sev, []).append(max(0, first_ack - st))
                except Exception:
                    pass

        labels = []; mttr_vals = []; mttd_vals = []; rows = []
        for sev in sorted(mttr_map.keys(), key=lambda k:int(k)):
            mttr_sec = int(np.mean(mttr_map[sev])) if mttr_map[sev] else 0
            mttd_sec = int(np.mean(mttd_map.get(sev, []))) if mttd_map.get(sev) else 0
            labels.append(self._SEVERITY_MAP.get(sev, sev))
            mttr_vals.append(mttr_sec)
            mttd_vals.append(mttd_sec)
            rows.append({'Severidade': self._SEVERITY_MAP.get(sev, sev), 'MTTR': self._fmt_seconds(mttr_sec), 'MTTD': self._fmt_seconds(mttd_sec)})

        chart_b64 = self._bars(labels, mttr_vals, mttd_vals)
        return self.render('mttr', {'chart_b64': chart_b64, 'rows': rows})

