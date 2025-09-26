from .base_collector import BaseCollector
from flask import current_app
import datetime as dt
import pandas as pd
from app.charting import generate_chart


class ResiliencePanelCollector(BaseCollector):
    """
    Painel de Resiliência (SLA Preciso) — Host-based

    - Respeita seleção de Cliente e Mês (usa all_hosts e period recebidos do ReportGenerator).
    - Calcula SLA por host reutilizando a infraestrutura existente de disponibilidade
      (correlação de eventos de PING) e a meta do cliente (sem entrada manual).
    - Oferece apenas o filtro "Host (contém)" e subperíodo opcional.

    custom_options suportadas:
      - host_name_contains: substring para filtrar o nome visível do host
      - period_sub_filter: full_month | last_24h | last_7d (default: full_month)
    """
    _DEFAULT_SEVERITIES = ['not_classified', 'info', 'warning', 'average', 'high', 'disaster']
    _SEVERITY_FILTER_MAP = {
        'not_classified': '0',
        'info': '1',
        'warning': '2',
        'average': '3',
        'high': '4',
        'disaster': '5',
    }


    def _tokenize(self, value):
        if not value:
            return []
        return [token.strip() for token in str(value).split(',') if token and token.strip()]

    def _fmt_seconds(self, total_seconds):
        try:
            total_seconds = int(total_seconds or 0)
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            return "00:00:00"

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

    def collect(self, all_hosts, period):
        opts = self.module_config.get('custom_options', {}) or {}
        host_contains = (opts.get('host_name_contains') or '').strip()
        host_exclude_raw = (opts.get('exclude_hosts_contains') or '')
        exclude_terms = [s.strip().lower() for s in str(host_exclude_raw).split(',') if s and str(s).strip()]
        trigger_contains_raw = (opts.get('trigger_contains') or '').strip()
        trigger_exclude_raw = (opts.get('trigger_exclude') or '').strip()
        tags_include_raw = (opts.get('tags_include') or '').strip()
        tags_exclude_raw = (opts.get('tags_exclude') or '').strip()
        selected_severities = opts.get('severities') if isinstance(opts.get('severities'), list) else None
        if selected_severities:
            severity_labels = [str(s) for s in selected_severities if str(s)]
        else:
            severity_labels = list(self._DEFAULT_SEVERITIES)
        severity_ids = [self._SEVERITY_FILTER_MAP.get(label) for label in severity_labels if label in self._SEVERITY_FILTER_MAP]
        trigger_include_tokens = [token.lower() for token in self._tokenize(trigger_contains_raw)]
        trigger_exclude_tokens = [token.lower() for token in self._tokenize(trigger_exclude_raw)]
        tag_include_tokens = [token.lower() for token in self._tokenize(tags_include_raw)]
        tag_exclude_tokens = [token.lower() for token in self._tokenize(tags_exclude_raw)]
        event_filters = {}
        if trigger_include_tokens:
            event_filters['trigger_contains'] = trigger_include_tokens
        if trigger_exclude_tokens:
            event_filters['trigger_exclude'] = trigger_exclude_tokens
        if tag_include_tokens:
            event_filters['tags_include'] = tag_include_tokens
        if tag_exclude_tokens:
            event_filters['tags_exclude'] = tag_exclude_tokens
        if severity_ids:
            event_filters['severity_ids'] = [sid for sid in severity_ids if sid is not None]
        event_filters = {k: v for k, v in event_filters.items() if v}


        decimals = int(opts.get('decimals') or 2)
        highlight = (opts.get('highlight_below_goal') is not False)
        sort_by = (opts.get('sort_by') or 'sla').lower()
        sort_asc = True if opts.get('sort_asc') is None else bool(opts.get('sort_asc'))
        try:
            top_n = int(opts.get('top_n')) if opts.get('top_n') else None
        except Exception:
            top_n = None
        show_chart = bool(opts.get('show_chart'))
        chart_color = opts.get('chart_color') or '#4e79a7'
        below_color = opts.get('below_color') or '#e15759'
        x_axis_0_100 = bool(opts.get('x_axis_0_100'))
        period = self._apply_period_subfilter(period, opts.get('period_sub_filter', 'full_month'))
        try:
            _s = dt.datetime.fromtimestamp(int(period['start'])).strftime('%d-%m-%Y')
            _e = dt.datetime.fromtimestamp(int(period['end'])).strftime('%d-%m-%Y')
            self._update_status(f"resilience_panel | período efetivo {_s} – {_e}")
        except Exception:
            pass

        # SLA alvo do cliente (sem entrada manual)
        try:
            target_sla = self.generator._get_client_sla_contract()
        except Exception:
            target_sla = None

        # Filtra hosts por "contém" (se informado)
        if host_contains:
            try:
                all_hosts = [h for h in (all_hosts or []) if host_contains.lower() in str(h.get('nome_visivel','')).lower()]
            except Exception:
                pass
        if exclude_terms:
            try:
                def _should_exclude(name):
                    nm = str(name or '').lower()
                    return any(t in nm for t in exclude_terms)
                all_hosts = [h for h in (all_hosts or []) if not _should_exclude(h.get('nome_visivel'))]
            except Exception:
                pass
        if not all_hosts:
            return self.render('resilience_panel', {
                'rows': [],
                'target_sla': target_sla,
                'period': period,
                'error': 'Nenhum host para calcular disponibilidade.'
            })

        self._update_status("Calculando disponibilidade por host (SLA)...")
        try:
            data, err = self.generator._collect_availability_data(all_hosts, period, target_sla, filters=event_filters or None)
        except Exception:
            current_app.logger.exception('[ResiliencePanel] Falha no cálculo de disponibilidade')
            data, err = None, 'Falha ao calcular disponibilidade.'

        if err or not data or 'df_sla_problems' not in data:
            return self.render('resilience_panel', {
                'rows': [],
                'target_sla': target_sla,
                'period': period,
                'error': err or 'Não foi possível obter dados de SLA.'
            })

        df = data['df_sla_problems']
        incidents_map_raw = data.get('incidents_by_host') or {}
        incidents_map = {}
        for key, value in incidents_map_raw.items():
            try:
                incidents_map[str(key)] = list(value) if isinstance(value, (list, tuple)) else []
            except Exception:
                incidents_map[str(key)] = []
        rows = []
        if isinstance(df, pd.DataFrame) and not df.empty:
            for _, r in df.iterrows():
                sla_val = None
                host_id = r.get('HostID')
                host_id_str = str(host_id) if host_id is not None else None
                try:
                    sla_val = float(r.get('SLA (%)'))
                except Exception:
                    sla_val = None
                dsecs = int(r.get('Downtime (s)') or 0)
                incident_count = len(incidents_map.get(host_id_str, [])) if host_id_str else 0
                rows.append({
                    'host': r.get('Host'),
                    'host_id': host_id_str,
                    'sla': sla_val,
                    'sla_str': (f"{sla_val:.{decimals}f}" if sla_val is not None else None),
                    'downtime': dsecs,
                    'downtime_hms': self._fmt_seconds(dsecs),
                    'incident_count': incident_count,
                })

        # Ordenação e Top N
        try:
            if sort_by in ('sla','downtime','host','incidents') and rows:
                rows.sort(key=(
                    (lambda x: (x['sla'] if x['sla'] is not None else -1.0)) if sort_by=='sla' else
                    (lambda x: x['downtime']) if sort_by=='downtime' else
                    (lambda x: x.get('incident_count', 0)) if sort_by=='incidents' else
                    (lambda x: str(x['host']).lower())
                ), reverse=(not sort_asc))
        except Exception:
            pass
        if top_n is not None and isinstance(top_n, int) and top_n > 0:
            rows = rows[:top_n]

        # Resumo criativo
        summary_text = None
        try:
            total = len(rows)
            below = 0
            if target_sla is not None:
                below = sum(1 for r in rows if (r['sla'] is not None and r['sla'] < float(target_sla)))
                ok = total - below
                summary_text = (
                    f"No período analisado, avaliamos {total} host(s). "
                    f"{ok} dentro da meta e {below} abaixo de {float(target_sla):.{decimals}f}% de SLA."
                )
            else:
                # Sem meta definida no cliente
                avg = None
                try:
                    vals = [r['sla'] for r in rows if r['sla'] is not None]
                    if vals:
                        avg = sum(vals)/len(vals)
                except Exception:
                    avg = None
                summary_text = (
                    f"No período analisado, avaliamos {total} host(s). "
                    + (f"Média de SLA: {avg:.{decimals}f}%" if avg is not None else "")
                )
        except Exception:
            summary_text = None

        # Opcional: grafico por host (barras horizontais com linha de meta)
        chart_b64 = None
        if show_chart and rows:
            try:
                df_chart = pd.DataFrame([
                    {'Host': r['host'], 'SLA': (float(r['sla']) if r['sla'] is not None else None)} for r in rows
                ])
                df_chart = df_chart.dropna(subset=['SLA'])
                if not df_chart.empty:
                    xlim = [0, 100] if x_axis_0_100 else None
                    chart_title = (self.module_config.get('title') or 'SLA por Host')
                    chart_b64 = generate_chart(
                        df_chart,
                        x_col='SLA',
                        y_col='Host',
                        title=chart_title,
                        x_label='SLA (%)',
                        chart_color=chart_color,
                        target_line=(float(target_sla) if target_sla is not None else None),
                        below_color=below_color,
                        xlim=xlim,
                        sort_ascending=sort_asc,
                    )
            except Exception:
                current_app.logger.warning('[ResiliencePanel] Falha ao gerar grafico de barras', exc_info=True)

        return self.render('resilience_panel', {
            'rows': rows,
            'target_sla': target_sla,
            'period': period,
            'summary_text': summary_text,
            'highlight_below_goal': bool(highlight),
            'chart_b64': chart_b64,
        })
