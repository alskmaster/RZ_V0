from .base_collector import BaseCollector
from flask import current_app
import datetime as dt
import pandas as pd
from app.charting import generate_chart
from app.zabbix_api import fazer_request_zabbix


class ResilienceServicesCollector(BaseCollector):
    """
    Painel de Resiliência por Serviços (SLA Preciso) — service.get + service.getsla

    custom_options suportadas:
      - serviceids: lista ou CSV de IDs de serviços (opcional)
      - service_name_contains: substring para filtrar nome (opcional)
      - tags: lista de objetos {tag, value} para filtrar serviços (opcional)
      - decimals: casas decimais para SLA (%)
      - highlight_below_goal: bool (default True)
      - sort_by: 'sla' | 'downtime' | 'service'
      - sort_asc: bool
      - top_n: int (limite de linhas)
      - show_trend: bool (default False)
      - trend_granularity: 'D'|'W' (default 'D')
      - chart_color, below_color, x_axis_0_100: mesmas semânticas do painel host-based
    """

    def _fmt_seconds(self, total_seconds):
        try:
            total_seconds = int(total_seconds or 0)
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            return "00:00:00"

    def _build_intervals(self, period, granularity):
        start = int(period['start']); end = int(period['end'])
        if granularity == 'W':
            # blocos de 7 dias a partir de start
            intervals = []
            cur = start
            while cur < end:
                nxt = min(end, cur + 7 * 24 * 3600)
                intervals.append({'from': cur, 'to': nxt})
                cur = nxt
            return intervals
        else:
            # diário
            day = 24 * 3600
            intervals = []
            cur = start
            while cur < end:
                nxt = min(end, cur + day)
                intervals.append({'from': cur, 'to': nxt})
                cur = nxt
            return intervals

    def _parse_service_ids(self, val):
        if val is None:
            return []
        if isinstance(val, (list, tuple)):
            return [str(x).strip() for x in val if str(x).strip()]
        return [s.strip() for s in str(val).split(',') if s and s.strip()]

    def _filter_by_tags(self, services, tags):
        if not tags:
            return services
        out = []
        for sv in (services or []):
            sv_tags = { (t.get('tag') or ''): (t.get('value') or '') for t in (sv.get('tags') or []) }
            ok = True
            for t in tags:
                k = (t or {}).get('tag'); v = (t or {}).get('value')
                if k is None:
                    continue
                if str(sv_tags.get(str(k), '')) != str(v or ''):
                    ok = False; break
            if ok:
                out.append(sv)
        return out

    def _services_discover(self, period, serviceids, name_contains, tags):
        # discover services
        if serviceids:
            # fetch only those
            body = {
                'jsonrpc': '2.0', 'method': 'service.get',
                'params': {
                    'output': ['serviceid', 'name'],
                    'serviceids': serviceids,
                    'selectTags': 'extend'
                },
                'auth': self.token, 'id': 1
            }
        else:
            params = {
                'output': ['serviceid', 'name'],
                'selectTags': 'extend',
                'sortfield': 'name'
            }
            if name_contains:
                params['search'] = {'name': name_contains}
                params['searchWildcardsEnabled'] = True
            body = {'jsonrpc': '2.0', 'method': 'service.get', 'params': params, 'auth': self.token, 'id': 1}
        data = fazer_request_zabbix(body, self.url) or []
        if not isinstance(data, list):
            return []
        if tags:
            data = self._filter_by_tags(data, tags)
        return data

    def _getsla(self, serviceids, intervals):
        if not serviceids or not intervals:
            return {}
        body = {
            'jsonrpc': '2.0', 'method': 'service.getsla',
            'params': {
                'serviceids': serviceids,
                'intervals': intervals,
                'filter': {'show_sla': 1, 'maintenance': False}
            },
            'auth': self.token, 'id': 1
        }
        resp = fazer_request_zabbix(body, self.url)
        return resp if isinstance(resp, dict) else {}

    def collect(self, all_hosts, period):
        opts = self.module_config.get('custom_options', {}) or {}
        decimals = int(opts.get('decimals') or 2)
        highlight = (opts.get('highlight_below_goal') is not False)
        sort_by = (opts.get('sort_by') or 'sla').lower()
        sort_asc = True if opts.get('sort_asc') is None else bool(opts.get('sort_asc'))
        try:
            top_n = int(opts.get('top_n')) if opts.get('top_n') else None
        except Exception:
            top_n = None
        show_trend = bool(opts.get('show_trend'))
        gran = (opts.get('trend_granularity') or 'D').upper()
        chart_color = opts.get('chart_color') or '#4e79a7'
        below_color = opts.get('below_color') or '#e15759'
        x_axis_0_100 = bool(opts.get('x_axis_0_100'))

        # SLA alvo do cliente (para destaque)
        try:
            target_sla = self.generator._get_client_sla_contract()
        except Exception:
            target_sla = None

        # descobrir serviços
        serviceids = self._parse_service_ids(opts.get('serviceids'))
        name_contains = (opts.get('service_name_contains') or '').strip()
        tags = opts.get('tags') or []

        self._update_status("resilience_services | descobrindo serviços...")
        services = self._services_discover(period, serviceids, name_contains, tags)
        if not services:
            return self.render('resilience_services', {
                'rows': [], 'target_sla': target_sla, 'period': period,
                'error': 'Nenhum serviço encontrado com os critérios fornecidos.'
            })

        # intervals
        intervals = [{'from': int(period['start']), 'to': int(period['end'])}]
        trend_intervals = self._build_intervals(period, gran) if show_trend else []

        self._update_status("resilience_services | consultando SLA...")
        ids = [s['serviceid'] for s in services]
        sla_resp_main = self._getsla(ids, intervals)
        sla_resp_trend = self._getsla(ids, trend_intervals) if trend_intervals else {}

        # map names
        name_map = {str(s['serviceid']): (s.get('name') or f"Service {s['serviceid']}") for s in services}

        def _extract_sla(resp, sid):
            try:
                # resp format expected: { serviceid: { 'sla': [ { 'sla': '99.99', 'downtime': 123, 'from':..., 'to':... } ] } }
                node = resp.get(str(sid)) or resp.get(int(sid))
                if not node:
                    return None, None
                sla_list = node.get('sla') or []
                if not sla_list:
                    return None, None
                it = sla_list[0]
                sla_val = float(it.get('sla')) if it.get('sla') is not None else None
                dt_sec = int(it.get('downtime') or 0)
                return sla_val, dt_sec
            except Exception:
                return None, None

        # build rows
        rows = []
        for sid in ids:
            sla_val, dt_sec = _extract_sla(sla_resp_main or {}, sid)
            rows.append({
                'service': name_map.get(str(sid), f'Service {sid}'),
                'sla': sla_val,
                'sla_str': (f"{sla_val:.{decimals}f}" if sla_val is not None else None),
                'downtime': dt_sec,
                'downtime_hms': self._fmt_seconds(dt_sec),
            })

        # sort/top
        try:
            keyfn = (lambda x: (x['sla'] if x['sla'] is not None else -1.0)) if sort_by=='sla' else \
                    (lambda x: x['downtime']) if sort_by=='downtime' else \
                    (lambda x: str(x['service']).lower())
            rows.sort(key=keyfn, reverse=(not sort_asc))
        except Exception:
            pass
        if top_n and top_n > 0:
            rows = rows[:top_n]

        # trend chart (optional) — only render when single service to keep clarity
        chart_b64 = None
        if show_trend and len(rows) == 1 and sla_resp_trend:
            sid = str(ids[0])
            try:
                points = (sla_resp_trend.get(sid) or {}).get('sla') or []
                if points:
                    df_chart = pd.DataFrame([{'Intervalo': i, 'SLA': float(p.get('sla')) if p.get('sla') is not None else None}
                                             for i, p in enumerate(points)])
                    df_chart = df_chart.dropna(subset=['SLA'])
                    if not df_chart.empty:
                        xlim = [0,100] if x_axis_0_100 else None
                        chart_b64 = generate_chart(
                            df_chart,
                            x_col='SLA', y_col='Intervalo',
                            title=self.module_config.get('title') or f"SLA — {rows[0]['service']}",
                            x_label='SLA (%)', chart_color=chart_color,
                            target_line=(float(target_sla) if target_sla is not None else None),
                            below_color=below_color, xlim=xlim,
                            sort_ascending=True,
                        )
            except Exception:
                current_app.logger.warning('[ResilienceServices] Falha ao gerar gráfico de tendência', exc_info=True)

        # resumo
        summary_text = None
        try:
            total = len(rows)
            below = 0
            if target_sla is not None:
                below = sum(1 for r in rows if (r['sla'] is not None and r['sla'] < float(target_sla)))
                ok = total - below
                summary_text = (
                    f"Avaliamos {total} serviço(s). {ok} dentro da meta e {below} abaixo de {float(target_sla):.{decimals}f}% de SLA.")
            else:
                vals = [r['sla'] for r in rows if r['sla'] is not None]
                avg = (sum(vals)/len(vals)) if vals else None
                summary_text = f"Avaliamos {total} serviço(s). " + (f"Média: {avg:.{decimals}f}%" if avg is not None else "")
        except Exception:
            pass

        return self.render('resilience_services', {
            'rows': rows,
            'target_sla': target_sla,
            'period': period,
            'summary_text': summary_text,
            'highlight_below_goal': bool(highlight),
            'chart_b64': chart_b64,
        })

