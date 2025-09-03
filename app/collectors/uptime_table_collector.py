from .base_collector import BaseCollector
from flask import current_app
import pandas as pd
import datetime as dt


class UptimeTableCollector(BaseCollector):
    """
    Uptime (Tabela): usa system.uptime (segundos desde o boot) para estimar o uptime
    no fim do período, contabiliza reinicializações no mês e exibe última reinicialização.

    custom_options:
      - host_name_contains: str
      - sort_by: 'Days'|'Reboots'|'Host' (default 'Days')
      - sort_asc: bool (default False)
      - top_n: int (0 = todos)
      - decimals: int (default 2)
    """

    def _format_uptime(self, seconds):
        try:
            seconds = int(float(seconds))
        except Exception:
            return ''
        days = seconds // 86400
        rem = seconds % 86400
        hours = rem // 3600
        minutes = (rem % 3600) // 60
        return f"{days}d {hours:02d}h{minutes:02d}m"

    def _collect_raw(self, all_hosts, period):
        host_ids = [h['hostid'] for h in all_hosts]
        host_map = {str(h['hostid']): h['nome_visivel'] for h in all_hosts}

        items = self.generator.get_items(host_ids, 'system.uptime', search_by_key=True)
        if not items:
            return pd.DataFrame(columns=['Host','Seconds','Days','Reboots','LastBoot'])

        item_ids = [it['itemid'] for it in items]
        trends = self.generator.get_trends_chunked(item_ids, period['start'], period['end'])
        if not isinstance(trends, list) or not trends:
            return pd.DataFrame(columns=['Host','Seconds','Days','Reboots','LastBoot'])

        df = pd.DataFrame(trends)
        if df.empty:
            return pd.DataFrame(columns=['Host','Seconds','Days','Reboots','LastBoot'])
        df['itemid'] = df['itemid'].astype(str)
        df['clock'] = pd.to_numeric(df['clock'], errors='coerce')
        df[['value_min','value_avg','value_max']] = df[['value_min','value_avg','value_max']].astype(float)

        # Para uptime consideramos value_max por intervalo; para valor final, pegamos o último clock
        last_by_item = df.sort_values('clock').groupby('itemid').tail(1)
        seconds_last = last_by_item[['itemid','value_max']].rename(columns={'value_max':'seconds'})

        # Reinicializações aproximadas: conta quantas vezes value_min < value_max anterior (queda)
        reboots = []
        for itemid, grp in df.sort_values('clock').groupby('itemid'):
            values = grp['value_max'].astype(float).tolist()
            cnt = 0
            for i in range(1, len(values)):
                try:
                    if values[i] < values[i-1] * 0.5:  # queda significativa
                        cnt += 1
                except Exception:
                    pass
            reboots.append({'itemid': itemid, 'reboots': cnt})
        df_reboots = pd.DataFrame(reboots)

        # Último boot: (fim do período - uptime_last)
        merged = seconds_last.merge(df_reboots, on='itemid', how='left')
        merged['hostid'] = merged['itemid'].map(lambda x: next((str(it['hostid']) for it in items if str(it['itemid'])==str(x)), None))
        merged['Host'] = merged['hostid'].map(lambda hid: host_map.get(str(hid), f'Host {hid}'))
        merged['Seconds'] = pd.to_numeric(merged['seconds'], errors='coerce')
        merged['Days'] = (merged['Seconds'] / 86400.0)
        try:
            end_dt = dt.datetime.fromtimestamp(int(period['end']))
            merged['LastBoot'] = merged['Seconds'].map(lambda s: (end_dt - dt.timedelta(seconds=float(s))).strftime('%d/%m/%Y %H:%M') if pd.notna(s) else '')
        except Exception:
            merged['LastBoot'] = ''
        merged['Reboots'] = pd.to_numeric(merged['reboots'], errors='coerce').fillna(0).astype(int)
        return merged[['Host','Seconds','Days','Reboots','LastBoot']]

    def collect(self, all_hosts, period):
        self._update_status("Coletando Uptime (tabela)...")
        opts = self.module_config.get('custom_options', {})
        host_contains = (opts.get('host_name_contains') or '').strip()
        sort_by = (opts.get('sort_by') or 'Days')
        sort_asc = bool(opts.get('sort_asc', False))
        top_n = int(opts.get('top_n') or 0)
        decimals = int(opts.get('decimals') or 2)

        df = self._collect_raw(all_hosts, period)
        if df is None or df.empty:
            return "<p><i>Sem dados de uptime para o período selecionado.</i></p>"

        if host_contains:
            df = df[df['Host'].astype(str).str.contains(host_contains, case=False, na=False)]

        if sort_by in df.columns:
            try:
                df = df.sort_values(by=sort_by, ascending=sort_asc)
            except Exception:
                pass

        if top_n and top_n > 0:
            df = df.head(top_n)

        # Formatação
        df_fmt = df.copy()
        try:
            df_fmt['Uptime'] = df_fmt['Seconds'].map(self._format_uptime)
            df_fmt['Days'] = pd.to_numeric(df_fmt['Days'], errors='coerce').map(lambda v: f"{v:.{decimals}f}" if pd.notna(v) else '')
            df_fmt = df_fmt[['Host','Uptime','Days','Reboots','LastBoot']]
        except Exception:
            pass

        html = df_fmt.to_html(classes='table', index=False, escape=False)
        return self.render('uptime_table', {'table_html': html})

