from .base_collector import BaseCollector
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64


class ITILAvailabilityCollector(BaseCollector):
    """
    ITIL Availability overlay (ASCII only)
    custom_options:
      - itemid: string (required)
      - value_type: int history (default 0)
      - severities: ['info','warning','average','high','disaster'] optional
    Renders a line of item history with shaded incident intervals from problem.get.
    """

    _SEVERITY_FILTER_MAP = {
        'info': '1', 'warning': '2', 'average': '3', 'high': '4', 'disaster': '5', 'not_classified': '0'
    }

    def _plot(self, df_hist, intervals):
        if df_hist is None or df_hist.empty:
            return None
        fig, ax = plt.subplots(figsize=(12, 4.8))
        ax.plot(df_hist['dt'], df_hist['value'], color='#1e88e5', linewidth=1.1)
        for (st, en) in intervals or []:
            try:
                ax.axvspan(pd.to_datetime(int(st), unit='s'), pd.to_datetime(int(en), unit='s'), color='red', alpha=0.12)
            except Exception:
                continue
        ax.set_xlabel('Tempo'); ax.set_ylabel('Valor')
        ax.grid(True, linestyle='--', alpha=0.3)
        fig.autofmt_xdate()
        buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight'); plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {}) or {}
        itemid = o.get('itemid')
        value_type = int(o.get('value_type') or 0)
        sevs = o.get('severities') or []
        ids = [self._SEVERITY_FILTER_MAP[s] for s in sevs if s in self._SEVERITY_FILTER_MAP]

        # Auto-discovery: if no itemid provided, try a default latency item
        if not itemid:
            try:
                hostids = [h['hostid'] for h in (all_hosts or [])]
                from app.zabbix_api import fazer_request_zabbix
                body = {
                    'jsonrpc':'2.0','method':'item.get',
                    'params':{
                        'output':['itemid','key_','hostid'],
                        'hostids': hostids,
                        'search': {'key_': o.get('key_search') or 'icmppingsec'},
                        'limit': 1
                    },
                    'auth': self.token,'id':1
                }
                data = fazer_request_zabbix(body, self.url)
                if isinstance(data, list) and data:
                    itemid = str(data[0].get('itemid'))
            except Exception:
                itemid = None

        if not itemid:
            return self.render('itil_availability', {'error': 'Informe itemid.'})

        from app.zabbix_api import fazer_request_zabbix
        # Map item->host
        hostid = None
        try:
            body_item = {'jsonrpc':'2.0','method':'item.get','params':{'output':['itemid','hostid'],'itemids':[str(itemid)]},'auth': self.token,'id':1}
            resp_item = fazer_request_zabbix(body_item, self.url)
            if isinstance(resp_item, list) and resp_item:
                hostid = str(resp_item[0].get('hostid'))
        except Exception:
            hostid = None

        # Fetch history
        df_hist = pd.DataFrame()
        try:
            body_hist = {
                'jsonrpc':'2.0','method':'history.get',
                'params':{
                    'output':['clock','value'],
                    'itemids':[str(itemid)],
                    'time_from': int(period['start']),
                    'time_till': int(period['end']),
                    'history': value_type,
                    'sortfield':'clock','sortorder':'ASC'
                },'auth': self.token,'id':1
            }
            data = fazer_request_zabbix(body_hist, self.url)
            if isinstance(data, list) and data:
                df_hist = pd.DataFrame(data)
                df_hist['value'] = pd.to_numeric(df_hist['value'], errors='coerce')
                df_hist['dt'] = pd.to_datetime(pd.to_numeric(df_hist['clock'], errors='coerce'), unit='s')
                df_hist = df_hist[['dt','value']].dropna().sort_values('dt')
        except Exception:
            df_hist = pd.DataFrame()

        # Fetch problems intervals + severity counts
        intervals = []
        sev_counts = {'0':0,'1':0,'2':0,'3':0,'4':0,'5':0}
        try:
            params = {'output':'extend','time_from': int(period['start']), 'time_till': int(period['end'])}
            if hostid:
                params['hostids'] = [hostid]
            if ids:
                params['severities'] = ids
            body_prob = {'jsonrpc':'2.0','method':'problem.get','params': params, 'auth': self.token, 'id': 1}
            probs = fazer_request_zabbix(body_prob, self.url)
            if isinstance(probs, list):
                for p in probs:
                    st = int(p.get('clock', period['start']))
                    en = int(p.get('r_clock', period['end'])) or int(period['end'])
                    if en < st: en = st
                    intervals.append((st, en))
                    sev = str(p.get('severity','0'))
                    if sev in sev_counts:
                        sev_counts[sev] += 1
        except Exception:
            intervals = []
            sev_counts = None

        chart_b64 = self._plot(df_hist, intervals)
        if (len(intervals) == 0) and (self.module_config.get('custom_options', {}) or {}).get('hide_if_empty'):
            return ""
        return self.render('itil_availability', {
            'chart_b64': chart_b64,
            'intervals': len(intervals),
            'itemid': str(itemid),
            'severity_counts': sev_counts,
        })
