from .base_collector import BaseCollector
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64


class CapacityForecastCollector(BaseCollector):
    """
    Capacity Forecast (ASCII only)
    custom_options:
      - itemids: list or CSV string of itemids
      - value_type: int history (default 0)
      - limit: float (threshold for projection)
      - projection_days: int (extend chart into future, default 30)
    Output: line chart per itemid and table with slope and ETA to limit.
    """

    def _line(self, series, limit=None, projection_days=30):
        if not series:
            return None
        fig, ax = plt.subplots(figsize=(12, 5))
        # Determine global time range
        min_dt = None; max_dt = None
        for df in series.values():
            if df.empty: continue
            _min = df['dt'].min(); _max = df['dt'].max()
            min_dt = _min if min_dt is None or _min < min_dt else min_dt
            max_dt = _max if max_dt is None or _max > max_dt else max_dt
        if max_dt is None:
            plt.close(fig); return None
        # Optional projection horizon
        end_dt = max_dt + pd.Timedelta(days=int(projection_days or 30))
        for label, df in series.items():
            if df.empty: continue
            ax.plot(df['dt'], df['value'], label=label, linewidth=1.1)
            # simple linear fit for projection
            try:
                x = (df['dt'].astype('int64') // 10**9).to_numpy()
                y = df['value'].to_numpy()
                if x.size >= 2:
                    a, b = np.polyfit(x, y, 1)
                    xp = np.array([x.max(), int(end_dt.timestamp())])
                    yp = a * xp + b
                    ax.plot(pd.to_datetime(xp, unit='s'), yp, linestyle='--', alpha=0.7)
            except Exception:
                pass
        if limit is not None:
            try:
                ax.axhline(float(limit), color='red', linewidth=1.0, linestyle=':')
            except Exception:
                pass
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.legend(loc='best', fontsize=9)
        ax.set_xlabel('Tempo'); ax.set_ylabel('Valor')
        fig.autofmt_xdate()
        buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight'); plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {}) or {}
        itemids = o.get('itemids') or []
        if isinstance(itemids, str):
            itemids = [s.strip() for s in itemids.split(',') if s.strip()]
        value_type = int(o.get('value_type') or 0)
        limit = o.get('limit')
        try:
            limit = float(limit) if limit not in (None, '') else None
        except Exception:
            limit = None
        projection_days = int(o.get('projection_days') or 30)

        # Auto-discovery: propose common capacity keys when none provided
        from app.zabbix_api import fazer_request_zabbix
        if not itemids:
            try:
                hostids = [h['hostid'] for h in (all_hosts or [])]
                patterns = o.get('key_search_list') or [
                    'vfs.fs.size[,pused]',
                    'vm.memory.size[pused]',
                    'system.cpu.util'
                ]
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
            return self.render('capacity_forecast', {'error': 'Informe itemids e limite (opcional).'})

        # Fetch raw history per itemid
        series = {}; rows = []
        from app.zabbix_api import fazer_request_zabbix
        # chunk itemids to avoid large payloads
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
                }, 'auth': self.token,'id':1
            }
            data = fazer_request_zabbix(body, self.url)
            if isinstance(data, list) and data:
                df = pd.DataFrame(data)
                df['itemid'] = df['itemid'].astype(str)
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                df['dt'] = pd.to_datetime(pd.to_numeric(df['clock'], errors='coerce'), unit='s')
                for iid, g in df.groupby('itemid'):
                    cur = series.get(iid)
                    g = g[['dt','value']].dropna().sort_values('dt')
                    series[iid] = pd.concat([cur, g]) if cur is not None else g

        # Optional: fetch item meta (key_, host) and infer default limit when not provided
        item_keys = {}; item_hosts = {}; item_names = {}
        try:
            body_keys = {
                'jsonrpc':'2.0','method':'item.get',
                'params':{'output':['itemid','key_','name','hostid'],'itemids': itemids},
                'auth': self.token,'id':1
            }
            resp_keys = fazer_request_zabbix(body_keys, self.url)
            if isinstance(resp_keys, list):
                for it in resp_keys:
                    iid = str(it.get('itemid'))
                    item_keys[iid] = it.get('key_') or ''
                    item_names[iid] = it.get('name') or ''
                    item_hosts[iid] = str(it.get('hostid') or '')
        except Exception:
            pass
        if limit is None:
            try:
                # if any key suggests percent utilization, assume 80 as planning threshold
                if any(('pused' in (k or '') or 'util' in (k or '')) for k in item_keys.values()):
                    limit = 80.0
            except Exception:
                pass

        # Compute linear regression stats and ETAs (slope per day)
        now_ts = int(dt.datetime.now().timestamp())
        horizon = 365*5*24*3600  # 5 years
        host_map = {str(h.get('hostid')): (h.get('nome_visivel') or h.get('hostname') or str(h.get('hostid'))) for h in (all_hosts or [])}
        for iid, df in series.items():
            if df is None or df.empty or df.shape[0] < 2:
                rows.append({'ItemID': iid, 'Item': f"{host_map.get(item_hosts.get(iid,''),'')} - {item_names.get(iid) or item_keys.get(iid,'')}".strip(' -'), 'Slope': None, 'Intercept': None, 'ETA': None, 'Trend': '-'})
                continue
            try:
                x = (df['dt'].astype('int64') // 10**9).to_numpy()
                y = df['value'].to_numpy()
                a, b = np.polyfit(x, y, 1)
                # slope per day
                slope_day = a * 86400.0
                trend = '↑' if slope_day > 0 else ('↓' if slope_day < 0 else '–')
                eta = None
                if limit is not None and a > 0:
                    sec_ts = (float(limit) - b) / a
                    if np.isfinite(sec_ts) and now_ts < sec_ts < now_ts + horizon:
                        eta_dt = dt.datetime.fromtimestamp(sec_ts)
                        eta = eta_dt.strftime('%d-%m-%Y %H:%M')
                rows.append({
                    'ItemID': iid,
                    'Item': f"{host_map.get(item_hosts.get(iid,''),'')} - {item_names.get(iid) or item_keys.get(iid,'')}".strip(' -'),
                    'Slope': round(float(slope_day), 4),
                    'Intercept': round(float(b), 3),
                    'ETA': eta,
                    'Trend': trend,
                })
            except Exception:
                rows.append({'ItemID': iid, 'Item': f"{host_map.get(item_hosts.get(iid,''),'')} - {item_names.get(iid) or item_keys.get(iid,'')}".strip(' -'), 'Slope': None, 'Intercept': None, 'ETA': None, 'Trend': '-'})

        # Risk classification and sorting
        crit_days = int(o.get('risk_threshold_critical_days') or 30)
        att_days = int(o.get('risk_threshold_attention_days') or 90)
        from datetime import datetime
        now = datetime.now()
        for r in rows:
            risk = 'Estável'
            if r.get('ETA'):
                try:
                    eta_dt = datetime.strptime(r['ETA'], '%d-%m-%Y %H:%M')
                    delta = (eta_dt - now).days
                    if delta < crit_days:
                        risk = 'Crítico'
                    elif delta < att_days:
                        risk = 'Atenção'
                except Exception:
                    pass
            elif r.get('Slope') and r['Slope'] > 0 and limit is not None:
                risk = 'Atenção'
            r['Risk'] = risk

        # Sort by risk then slope desc
        def _risk_rank(x):
            return {'Crítico': 0, 'Atenção': 1, 'Estável': 2}.get(x or 'Estável', 2)
        rows = sorted(rows, key=lambda r: (_risk_rank(r.get('Risk')), -(r.get('Slope') or 0)))

        # Summary and hide-if-empty
        counts = {
            'critico': sum(1 for r in rows if r.get('Risk') == 'Crítico'),
            'atencao': sum(1 for r in rows if r.get('Risk') == 'Atenção'),
            'estavel': sum(1 for r in rows if r.get('Risk') == 'Estável'),
        }
        if (counts['critico'] + counts['atencao']) == 0 and o.get('hide_if_empty'):
            return ""

        chart_b64 = self._line(series, limit=limit, projection_days=projection_days)
        return self.render('capacity_forecast', {
            'chart_b64': chart_b64,
            'rows': rows,
            'limit': limit,
            'summary': counts,
            'crit_days': crit_days,
            'att_days': att_days,
        })
