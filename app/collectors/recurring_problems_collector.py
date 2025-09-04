from .base_collector import BaseCollector
import pandas as pd


class RecurringProblemsCollector(BaseCollector):
    """
    Gestao de Problemas Recorrentes (ASCII only)
    - Conta problemas por triggerid e lista os que ultrapassam o limiar.
    custom_options:
      - min_count: int (default 3)
      - severities: ['info','warning','average','high','disaster'] (opcional)
      - host_name_contains: filtro textual (opcional)
      - period_sub_filter: full_month | last_24h | last_7d
    """

    _SEVERITY_FILTER_MAP = {
        'info': '1', 'warning': '2', 'average': '3', 'high': '4', 'disaster': '5', 'not_classified': '0'
    }

    def _apply_period_subfilter(self, period, sub):
        start, end = period['start'], period['end']
        from datetime import datetime
        now = int(datetime.now().timestamp())
        if sub == 'last_24h':
            end = now; start = end - 24*3600
        elif sub == 'last_7d':
            end = now; start = end - 7*24*3600
        return {'start': int(start), 'end': int(end)}

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {}) or {}
        min_count = int(o.get('min_count') or 3)
        sevs = o.get('severities') or []
        ids = [self._SEVERITY_FILTER_MAP[s] for s in sevs if s in self._SEVERITY_FILTER_MAP]
        host_contains = (o.get('host_name_contains') or '').strip()
        period = self._apply_period_subfilter(period, o.get('period_sub_filter', 'full_month'))

        if host_contains:
            try:
                all_hosts = [h for h in (all_hosts or []) if host_contains.lower() in str(h.get('nome_visivel','')).lower()]
            except Exception:
                pass
        if not all_hosts:
            return self.render('recurring_problems', {'rows': [], 'min_count': min_count})

        ids_hosts = [h['hostid'] for h in all_hosts]
        evs = self.generator.obter_eventos_wrapper(ids_hosts, period, 'hostids')
        if evs is None:
            return self.render('recurring_problems', {'rows': [], 'min_count': min_count, 'error': 'Falha ao coletar eventos.'})

        df = pd.DataFrame(evs)
        if df.empty:
            return self.render('recurring_problems', {'rows': [], 'min_count': min_count})
        for c in ('source','object','value','severity'):
            if c in df.columns: df[c]=df[c].astype(str)
        df = df[(df['source']=='0') & (df['object']=='0') & (df['value']=='1')]
        if ids:
            df = df[df['severity'].astype(str).isin(ids)]
        if df.empty:
            return self.render('recurring_problems', {'rows': [], 'min_count': min_count})

        df['tid'] = df.apply(lambda r: str(r.get('objectid') or r.get('triggerid')), axis=1)
        counts = df.groupby('tid').size().reset_index(name='count')
        name_choices = df.groupby(['tid','name']).size().reset_index(name='n')
        top_names = name_choices.sort_values(['tid','n'], ascending=[True,False]).drop_duplicates('tid')
        merged = counts.merge(top_names[['tid','name']], on='tid', how='left')
        merged = merged[merged['count'] >= min_count].sort_values('count', ascending=False)
        rows = merged.rename(columns={'name':'Trigger','count':'Ocorrencias'}).to_dict('records')
        return self.render('recurring_problems', {'rows': rows, 'min_count': min_count})

