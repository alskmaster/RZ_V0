from .base_collector import BaseCollector
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64


class CriticalPerformanceCollector(BaseCollector):
    """
    Desempenho Critico (ASCII only)
    - Plota series historicas (history.get) para itemids informados.
    custom_options:
      - itemids: lista de ids (strings) ou CSV
      - value_type: int history (default 0)
      - period_sub_filter: full_month | last_24h | last_7d
      - title_suffix: texto opcional por serie
    """

    def _apply_period_subfilter(self, period, sub):
        start, end = period['start'], period['end']
        now = int(dt.datetime.now().timestamp())
        if sub == 'last_24h': end = now; start = end - 24*3600
        elif sub == 'last_7d': end = now; start = end - 7*24*3600
        return {'start': int(start), 'end': int(end)}

    def _line(self, series_dict):
        if not series_dict: return None
        fig, ax = plt.subplots(figsize=(12, 4.8))
        for label, df in series_dict.items():
            if df.empty: continue
            ax.plot(df['dt'], df['value'], label=label, linewidth=1.2)
        ax.set_xlabel('Tempo'); ax.set_ylabel('Valor')
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.legend(loc='best', fontsize=9)
        fig.autofmt_xdate()
        buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight'); plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {}) or {}
        itemids = o.get('itemids') or []
        if isinstance(itemids, str):
            itemids = [s.strip() for s in itemids.split(',') if s.strip()]
        value_type = int(o.get('value_type') or 0)
        period = self._apply_period_subfilter(period, o.get('period_sub_filter', 'full_month'))

        # Auto-discovery: when no itemids provided, try common keys on client's hosts
        if not itemids:
            try:
                hostids = [h['hostid'] for h in (all_hosts or [])]
                patterns = o.get('key_search_list') or [
                    'vm.memory.size[pused]',
                    'vfs.fs.size[,pused]',
                    'system.cpu.util',
                    'icmppingsec'
                ]
                from app.zabbix_api import fazer_request_zabbix
                found = []
                for pat in patterns:
                    body = {
                        'jsonrpc':'2.0','method':'item.get',
                        'params':{
                            'output':['itemid','key_'],
                            'hostids': hostids,
                            'search': {'key_': pat},
                            'limit': 50
                        },
                        'auth': self.token,'id':1
                    }
                    data = fazer_request_zabbix(body, self.url)
                    if isinstance(data, list):
                        for it in data:
                            iid = str(it.get('itemid'))
                            if iid and iid not in found:
                                found.append(iid)
                    if len(found) >= 50:
                        break
                itemids = found[:50]
            except Exception:
                itemids = []

        if not itemids:
            return self.render('critical_performance', {'error': 'Informe itemids para consulta.'})

        # history.get raw series
        series_dict = {}
        for chunk in [itemids[i:i+50] for i in range(0, len(itemids), 50)]:
            body = {
                'jsonrpc':'2.0','method':'history.get',
                'params':{
                    'output':['itemid','clock','value'],
                    'itemids': chunk,
                    'time_from': int(period['start']),
                    'time_till': int(period['end']),
                    'history': value_type,
                    'sortfield':'clock','sortorder':'ASC'
                },
                'auth': self.token,'id':1
            }
            from app.zabbix_api import fazer_request_zabbix
            data = fazer_request_zabbix(body, self.url)
            if isinstance(data, list) and data:
                df = pd.DataFrame(data)
                df['itemid'] = df['itemid'].astype(str)
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                df['dt'] = pd.to_datetime(pd.to_numeric(df['clock'], errors='coerce'), unit='s')
                for iid, g in df.groupby('itemid'):
                    cur = series_dict.get(iid)
                    g = g[['dt','value']].sort_values('dt')
                    series_dict[iid] = pd.concat([cur, g]) if cur is not None else g

        # Apply min points threshold and build summary
        min_points = int(o.get('min_points') or 10)
        filtered = {}
        total_series = len(series_dict)
        for k, df in series_dict.items():
            if df is not None and not df.empty and int(df.shape[0]) >= min_points:
                filtered[k] = df
        active_series = len(filtered)
        inactive_series = total_series - active_series
        series_dict = filtered
        if active_series == 0 and o.get('hide_if_empty'):
            return ""

        # Optional: enrich labels with key_/name
        labels = {}
        try:
            if series_dict:
                itemids_all = list(series_dict.keys())
                body = {'jsonrpc':'2.0','method':'item.get','params':{'output':['itemid','key_','name'],'itemids': itemids_all},'auth': self.token,'id':1}
                from app.zabbix_api import fazer_request_zabbix
                meta = fazer_request_zabbix(body, self.url)
                if isinstance(meta, list):
                    for it in meta:
                        labels[str(it.get('itemid'))] = it.get('name') or it.get('key_') or str(it.get('itemid'))
        except Exception:
            pass
        chart_b64 = self._line(series_dict)
        rows = [{'ItemID': k, 'Item': labels.get(k, k), 'Pontos': int(v.shape[0])} for k,v in series_dict.items()]
        summary = {'series_total': int(total_series), 'series_ativas': int(active_series), 'series_inativas': int(inactive_series)}
        return self.render('critical_performance', {'chart_b64': chart_b64, 'rows': rows, 'summary': summary})
