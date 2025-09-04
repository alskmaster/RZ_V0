from .base_collector import BaseCollector
import pandas as pd
import datetime as dt


class ExecutiveSummaryCollector(BaseCollector):
    """
    Executive Summary (ASCII only)
    custom_options:
      - top_n_incidents: int (default 5)
    Produces simple KPI cards from available data and events.
    """

    def collect(self, all_hosts, period):
        top_n = int((self.module_config.get('custom_options') or {}).get('top_n_incidents') or 5)
        kpis = []

        # Hosts count
        total_hosts = len(all_hosts or [])
        kpis.append({'label': 'Total de Hosts', 'value': str(total_hosts)})

        # SLA average if available in cached_data from availability modules
        sla_avg_val = None
        try:
            df_sla = self.generator.cached_data.get('df_sla_problems')
            if df_sla is not None and hasattr(df_sla, 'empty') and not df_sla.empty:
                sla_avg_val = float(df_sla['SLA (%)'].mean())
        except Exception:
            pass
        if sla_avg_val is not None:
            kpis.append({'label': 'SLA Médio', 'value': f"{sla_avg_val:.2f}%"})

        # Incidents summary via eventos wrapper
        incidents_rows = []
        try:
            evs = self.generator.obter_eventos_wrapper([h['hostid'] for h in (all_hosts or [])], period, 'hostids')
            if isinstance(evs, list) and evs:
                df = pd.DataFrame(evs)
                df = df[(df.get('source','0').astype(str)=='0') & (df.get('object','0').astype(str)=='0')]
                df_prob = df[df.get('value','0').astype(str)=='1']
                kpis.append({'label': 'Total de Incidentes', 'value': str(int(df_prob.shape[0]))})
                if not df_prob.empty:
                    # Top offenders by count
                    host_map = {}
                    try:
                        for h in (all_hosts or []):
                            host_map[str(h.get('hostid'))] = h.get('nome_visivel') or h.get('hostname') or str(h.get('hostid'))
                    except Exception:
                        pass
                    # objectid/triggerid per host
                    df_prob['hostid'] = df_prob.get('hosts').apply(lambda arr: str((arr or [{}])[0].get('hostid')) if isinstance(arr, list) and arr else None)
                    top = df_prob.groupby('hostid').size().reset_index(name='count').sort_values('count', ascending=False).head(top_n)
                    for _, r in top.iterrows():
                        name = host_map.get(str(r['hostid']), f"Host {r['hostid']}")
                        incidents_rows.append({'Host': name, 'Incidentes': int(r['count'])})
        except Exception:
            pass

        return self.render('executive_summary', {'kpis': kpis, 'top_incidents': incidents_rows})

