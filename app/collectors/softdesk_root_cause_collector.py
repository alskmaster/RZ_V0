from .base_collector import BaseCollector
from flask import current_app
import datetime as dt
import pandas as pd
import requests
import re
import time


class SoftdeskRootCauseCollector(BaseCollector):
    """Integra tickets do Softdesk com incidentes reconhecidos no Zabbix."""

    _SEVERITY_MAP = {
        '0': 'Nao Classificado',
        '1': 'Informacao',
        '2': 'Atencao',
        '3': 'Media',
        '4': 'Alta',
        '5': 'Desastre'
    }
    _SEVERITY_FILTER_MAP = {
        'info': '1',
        'warning': '2',
        'average': '3',
        'high': '4',
        'disaster': '5',
        'not_classified': '0'
    }
    _TICKET_RE = re.compile(r"\b\d{5,6}\b")

    def _apply_period_subfilter(self, period, subfilter):
        start, end = int(period['start']), int(period['end'])
        now = int(dt.datetime.now().timestamp())
        if subfilter == 'last_24h':
            end = now
            start = now - 24 * 3600
        elif subfilter == 'last_7d':
            end = now
            start = now - 7 * 24 * 3600
        return {'start': start, 'end': end}

    def _format_ts(self, ts):
        try:
            return dt.datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            return 'N/A'

    def _format_duration(self, seconds):
        try:
            seconds = max(0, int(seconds or 0))
        except Exception:
            seconds = 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _format_datetime_parts(self, date_part, time_part=None):
        if not date_part:
            return None
        try:
            if time_part:
                iso = f"{date_part}T{time_part}"
                dt_obj = dt.datetime.fromisoformat(iso)
            else:
                dt_obj = dt.datetime.fromisoformat(date_part)
            return dt_obj.strftime('%d/%m/%Y %H:%M:%S') if time_part else dt_obj.strftime('%d/%m/%Y')
        except Exception:
            if time_part:
                return f"{date_part} {time_part}"
            return date_part

    def _tokenize(self, value):
        if not value:
            return []
        if isinstance(value, (list, tuple)):
            return [str(token).strip() for token in value if str(token).strip()]
        return [token.strip() for token in str(value).split(',') if token and token.strip()]

    def _parse_field_codes(self, raw_value, default_codes):
        codes = []
        for token in self._tokenize(raw_value):
            try:
                codes.append(int(token))
            except Exception:
                continue
        if not codes:
            if isinstance(default_codes, (list, tuple)):
                return [int(c) for c in default_codes if isinstance(c, int)]
            try:
                return [int(default_codes)]
            except Exception:
                return []
        return codes

    def _extract_ticket_ids(self, acknowledges):
        tickets = set()
        for ack in acknowledges or []:
            try:
                message = ack.get('message') or ''
                tickets.update(self._TICKET_RE.findall(str(message)))
            except Exception:
                continue
        return sorted(tickets)

    def _fetch_softdesk_tickets(self, ticket_ids, base_url, api_key, note_codes=None, root_codes=None, protocol_codes=None):
        ids = []
        for tid in ticket_ids or []:
            tid_str = str(tid).strip()
            if tid_str:
                ids.append(tid_str)
        results = {}
        note_codes = self._parse_field_codes(note_codes, [5])
        root_codes = self._parse_field_codes(root_codes, [6])
        protocol_codes = self._parse_field_codes(protocol_codes, [7])

        if not ids:
            return results
        session = requests.Session()
        headers = {'hash_api': api_key}
        base = base_url.rstrip('/')
        sorted_ids = sorted(set(ids))
        for idx, tid in enumerate(sorted_ids):
            try:
                url = f"{base}/api/api.php/chamado?codigo={tid}"
                resp = session.get(url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    current_app.logger.warning(
                        f"[SoftdeskRootCause] Falha ao consultar chamado {tid}: status {resp.status_code}"
                    )
                    continue
                data = resp.json()
                if not isinstance(data, dict) or 'objeto' not in data:
                    continue
                obj = data['objeto']
                campos = obj.get('campos_costumizaveis') or []

                def _get_custom(code_list):
                    for code in code_list or []:
                        for campo in campos:
                            try:
                                if int(campo.get('campo_customizavel', {}).get('codigo')) == int(code):
                                    raw_val = (campo.get('descricao') or campo.get('valor') or campo.get('texto') or '').strip()
                                    if raw_val:
                                        return raw_val
                            except Exception:
                                continue
                    return ''

                results[tid] = {
                    'id_chamado': obj.get('codigo'),
                    'titulo': obj.get('titulo'),
                    'cliente': (obj.get('cliente') or {}).get('nome'),
                    'prioridade': (obj.get('prioridade') or {}).get('descricao'),
                    'status': (obj.get('status') or {}).get('descricao'),
                    'atendente': (obj.get('atendente') or {}).get('nome'),
                    'abertura': self._format_datetime_parts(obj.get('data_abertura'), obj.get('hora_abertura')),
                    'encerramento': self._format_datetime_parts(obj.get('data_encerramento'), obj.get('hora_encerramento')),
                    'nota_fechamento': _get_custom(note_codes) or None,
                    'causa_raiz': _get_custom(root_codes) or None,
                    'protocolo_operadora': _get_custom(protocol_codes) or None,
                }
            except requests.RequestException as exc:
                current_app.logger.warning(
                    f"[SoftdeskRootCause] Erro de conexao ao consultar chamado {tid}: {exc}"
                )
            except Exception as exc:
                current_app.logger.warning(
                    f"[SoftdeskRootCause] Erro ao processar chamado {tid}: {exc}"
                )
            if idx < len(sorted_ids) - 1:
                time.sleep(1)
        return results

    def collect(self, all_hosts, period):
        client = getattr(self.generator, 'client', None)
        base_url = getattr(client, 'softdesk_base_url', None) if client else None
        api_key = getattr(client, 'softdesk_api_key', None) if client else None
        if not client or not getattr(client, 'softdesk_enabled', False):
            return self.render(
                'softdesk_root_cause',
                {'error': 'Integracao com Softdesk nao habilitada para o cliente.', 'tickets': []}
            )
        if not base_url or not api_key:
            return self.render(
                'softdesk_root_cause',
                {'error': 'Credenciais do Softdesk ausentes.', 'tickets': []}
            )

        options = self.module_config.get('custom_options', {}) or {}
        selected_names = options.get('severities', ['info', 'warning', 'average', 'high', 'disaster'])
        severity_ids = [self._SEVERITY_FILTER_MAP[s] for s in selected_names if s in self._SEVERITY_FILTER_MAP]
        sub_filter = options.get('period_sub_filter', 'full_month')
        ack_filter = (options.get('ack_filter') or 'all').lower()
        host_contains = (options.get('host_name_contains') or '').strip()
        host_exclude = (options.get('exclude_hosts_contains') or '').strip()
        problem_contains = (options.get('problem_contains') or '').strip()
        problem_exclude = (options.get('exclude_problem_contains') or '').strip()
        tags_include = (options.get('tags_include') or '').strip()
        tags_exclude = (options.get('tags_exclude') or '').strip()
        group_by = (options.get('group_by') or 'tickets').lower()
        if group_by not in ('tickets', 'host'):
            group_by = 'tickets'
        show_events_table = options.get('show_events_table')
        if isinstance(show_events_table, str):
            show_events_table = show_events_table.lower() not in ('false', '0', 'no')
        show_events_table = True if show_events_table is None else bool(show_events_table)

        note_field_codes = self._parse_field_codes(options.get('note_field_codes'), [5])
        root_field_codes = self._parse_field_codes(options.get('root_cause_field_codes'), [6])
        protocol_field_codes = self._parse_field_codes(options.get('protocol_field_codes'), [7])

        top_n = options.get('top_n_tickets')
        sort_by = (options.get('sort_by') or 'duration').lower()
        period = self._apply_period_subfilter(period, sub_filter)

        host_ids = [h['hostid'] for h in all_hosts]
        host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}

        events = self.generator.obter_eventos(host_ids, period, 'hostids', include_acks=True)
        if events is None:
            self._update_status('Erro ao coletar eventos do Zabbix para o Softdesk.')
            return self.render(
                'softdesk_root_cause',
                {'error': 'Falha ao coletar eventos para o periodo.', 'tickets': []}
            )

        df = pd.DataFrame(events)
        if df.empty:
            return self.render('softdesk_root_cause', {
                'tickets': [],
                'period': period,
                'period_label': f"{self._format_ts(period['start'])} - {self._format_ts(period['end'])}",
                'selected_severities': selected_names
            })

        for col in ('value', 'severity', 'source', 'object'):
            if col in df.columns:
                df[col] = df[col].astype(str)
        mask = pd.Series([True] * len(df))
        if 'source' in df.columns:
            mask &= (df['source'] == '0')
        if 'object' in df.columns:
            mask &= (df['object'] == '0')
        if 'value' in df.columns:
            mask &= (df['value'] == '1')
        df = df[mask]
        if severity_ids:
            df = df[df['severity'].astype(str).isin(severity_ids)]
        if df.empty:
            return self.render('softdesk_root_cause', {
                'tickets': [],
                'period': period,
                'period_label': f"{self._format_ts(period['start'])} - {self._format_ts(period['end'])}",
                'selected_severities': selected_names
            })

        df['trigger_ref'] = df['objectid'].where(df['objectid'].notna(), df.get('triggerid'))
        df['clock'] = pd.to_numeric(df['clock'], errors='coerce').fillna(0).astype(int)
        df['host_name'] = df['hosts'].apply(
            lambda hs: host_map.get((hs[0] or {}).get('hostid')) if isinstance(hs, list) and hs else None
        )
        df['severity_name'] = df['severity'].astype(str).map(self._SEVERITY_MAP).fillna('Desconhecido')

        if host_contains:
            df = df[df['host_name'].astype(str).str.contains(host_contains, case=False, na=False)]
        if host_exclude:
            tokens = [tok.strip().lower() for tok in host_exclude.split(',') if tok.strip()]
            if tokens:
                df = df[~df['host_name'].astype(str).str.lower().apply(lambda nm: any(tok in nm for tok in tokens))]
        if problem_contains:
            df = df[df['name'].astype(str).str.contains(problem_contains, case=False, na=False)]
        if problem_exclude:
            tokens = [tok.strip().lower() for tok in problem_exclude.split(',') if tok.strip()]
            if tokens:
                df = df[~df['name'].astype(str).str.lower().apply(lambda nm: any(tok in nm for tok in tokens))]

        if 'acknowledged' in df.columns and ack_filter in {'only_acked', 'only_unacked'}:
            flag = '1' if ack_filter == 'only_acked' else '0'
            df = df[df['acknowledged'].astype(str) == flag]

        if df.empty:
            return self.render('softdesk_root_cause', {
                'tickets': [],
                'period': period,
                'period_label': f"{self._format_ts(period['start'])} - {self._format_ts(period['end'])}",
                'selected_severities': selected_names,
                'info': 'Nenhum incidente reconhecido com ticket do Softdesk no periodo.'
            })

        if tags_include or tags_exclude:
            if 'tags' not in df.columns:
                try:
                    if 'eventid' in df.columns and len(df['eventid']) > 0:
                        tags_map = self.generator.obter_eventos_tags_details(df['eventid'].astype(str).tolist()) or {}
                        df['tags'] = df['eventid'].astype(str).map(lambda eid: tags_map.get(str(eid), []))
                    else:
                        df['tags'] = None
                except Exception:
                    df['tags'] = None
            df['tags'] = df['tags'].apply(lambda value: value if isinstance(value, list) else [])
            df['_tag_strs'] = df['tags'].apply(
                lambda lst: [f"{(item or {}).get('tag', '')}={(item or {}).get('value', '')}" for item in lst]
            )
            if tags_include:
                inc_tokens = [tok.strip().lower() for tok in tags_include.split(',') if tok.strip()]
                if inc_tokens:
                    df = df[df['_tag_strs'].apply(
                        lambda tags: any(any(tok in t.lower() for t in tags) for tok in inc_tokens)
                    )]
            if tags_exclude:
                exc_tokens = [tok.strip().lower() for tok in tags_exclude.split(',') if tok.strip()]
                if exc_tokens:
                    df = df[~df['_tag_strs'].apply(
                        lambda tags: any(any(tok in t.lower() for t in tags) for tok in exc_tokens)
                    )]
            df = df.drop(columns=['_tag_strs'])
        if df.empty:
            return self.render('softdesk_root_cause', {
                'tickets': [],
                'period': period,
                'period_label': f"{self._format_ts(period['start'])} - {self._format_ts(period['end'])}",
                'selected_severities': selected_names,
                'info': 'Nenhum incidente reconhecido com ticket do Softdesk no periodo.'
            })

        if 'acknowledges' not in df.columns:
            df['acknowledges'] = None
        df['ticket_ids'] = df['acknowledges'].apply(self._extract_ticket_ids)
        df = df[df['ticket_ids'].map(bool)]
        if df.empty:
            return self.render('softdesk_root_cause', {
                'tickets': [],
                'period': period,
                'period_label': f"{self._format_ts(period['start'])} - {self._format_ts(period['end'])}",
                'selected_severities': selected_names,
                'info': 'Nenhum incidente reconhecido com ticket do Softdesk no periodo.'
            })

        df = df.explode('ticket_ids')
        df['ticket_ids'] = df['ticket_ids'].astype(str)

        try:
            problems_only = df.to_dict('records')
            correlated = self.generator._correlate_problems(problems_only, events, period)
        except Exception:
            correlated = []
        duration_map = {}
        for item in correlated or []:
            try:
                tid = str(item.get('triggerid'))
                start = int(item.get('start'))
                duration_map[(tid, start)] = int(item.get('end', start))
            except Exception:
                continue
        period_end = int(period['end'])

        def _end_ts(row):
            key = (str(row.get('trigger_ref')), int(row.get('clock', 0)))
            end_ts = duration_map.get(key)
            if end_ts is None:
                return period_end
            return max(int(end_ts), int(row.get('clock', 0)))

        df['end_ts'] = df.apply(_end_ts, axis=1)
        df['duration'] = (df['end_ts'] - df['clock']).clip(lower=0)
        df['formatted_start'] = df['clock'].apply(self._format_ts)
        df['formatted_end'] = df['end_ts'].apply(self._format_ts)
        df['formatted_duration'] = df['duration'].apply(self._format_duration)

        ticket_details = self._fetch_softdesk_tickets(
            df['ticket_ids'].unique().tolist(),
            base_url,
            api_key,
            note_codes=note_field_codes,
            root_codes=root_field_codes,
            protocol_codes=protocol_field_codes
        )

        grouped = []
        ticket_details_map = {str(k): v for k, v in (ticket_details or {}).items()}

        if group_by == 'host':
            host_groups = df.groupby('host_name', dropna=False)
            for host_name, group in host_groups:
                host_label = host_name or 'Desconhecido'
                intervals = []
                for _, raw in group.iterrows():
                    start_val = int(raw.get('clock', 0))
                    end_val = int(raw.get('end_ts', start_val))
                    intervals.append((start_val, end_val))
                intervals.sort()
                merged = []
                for start_val, end_val in intervals:
                    if not merged or start_val > merged[-1][1]:
                        merged.append([start_val, end_val])
                    else:
                        merged[-1][1] = max(merged[-1][1], end_val)
                total_seconds = sum(end_val - start_val for start_val, end_val in merged)

                events_rows = []
                for _, row in group.sort_values('clock').iterrows():
                    events_rows.append({
                        'ticket_id': str(row.get('ticket_ids') or ''),
                        'host': row.get('host_name') or 'Desconhecido',
                        'problem': row.get('name') or f"Trigger {row.get('trigger_ref')}",
                        'severity': row.get('severity_name'),
                        'start': row.get('formatted_start'),
                        'end': row.get('formatted_end'),
                        'duration': row.get('formatted_duration')
                    })

                ticket_ids = sorted({str(val) for val in group['ticket_ids'].dropna().astype(str)})
                ticket_details_list = []
                for tid in ticket_ids:
                    ticket_details_list.append({
                        'ticket_id': tid,
                        'softdesk': ticket_details_map.get(tid)
                    })

                grouped.append({
                    'group_type': 'host',
                    'ticket_id': host_label,
                    'softdesk': None,
                    'hosts': [host_label],
                    'tickets': ticket_ids,
                    'ticket_details': ticket_details_list,
                    'total_duration_seconds': int(total_seconds),
                    'total_duration': self._format_duration(total_seconds),
                    'events': events_rows
                })
        else:
            for ticket_id, group in df.groupby('ticket_ids'):
                intervals = []
                for _, raw in group.iterrows():
                    start_val = int(raw.get('clock', 0))
                    end_val = int(raw.get('end_ts', start_val))
                    intervals.append((start_val, end_val))
                intervals.sort()
                merged = []
                for start_val, end_val in intervals:
                    if not merged or start_val > merged[-1][1]:
                        merged.append([start_val, end_val])
                    else:
                        merged[-1][1] = max(merged[-1][1], end_val)
                total_seconds = sum(end_val - start_val for start_val, end_val in merged)

                events_rows = []
                for _, row in group.sort_values('clock').iterrows():
                    events_rows.append({
                        'ticket_id': str(ticket_id),
                        'host': row.get('host_name') or 'Desconhecido',
                        'problem': row.get('name') or f"Trigger {row.get('trigger_ref')}",
                        'severity': row.get('severity_name'),
                        'start': row.get('formatted_start'),
                        'end': row.get('formatted_end'),
                        'duration': row.get('formatted_duration')
                    })

                ticket_id_str = str(ticket_id)
                ticket_info = ticket_details_map.get(ticket_id_str)

                grouped.append({
                    'group_type': 'ticket',
                    'ticket_id': ticket_id_str,
                    'softdesk': ticket_info,
                    'hosts': sorted({row.get('host_name') or 'Desconhecido' for _, row in group.iterrows()}),
                    'tickets': [ticket_id_str],
                    'ticket_details': [{
                        'ticket_id': ticket_id_str,
                        'softdesk': ticket_info
                    }],
                    'total_duration_seconds': int(total_seconds),
                    'total_duration': self._format_duration(total_seconds),
                    'events': events_rows
                })

        if sort_by == 'tickets':
            if group_by == 'host':
                grouped.sort(key=lambda item: item['ticket_id'])
            else:
                grouped.sort(key=lambda item: item['ticket_id'])
        else:
            grouped.sort(key=lambda item: item['total_duration_seconds'], reverse=True)
        if top_n:
            try:
                top_n_val = int(top_n)
                if top_n_val > 0:
                    grouped = grouped[:top_n_val]
            except Exception:
                pass

        period_label = f"{self._format_ts(period['start'])} - {self._format_ts(period['end'])}"
        return self.render('softdesk_root_cause', {
            'tickets': grouped,
            'period': period,
            'period_label': period_label,
            'selected_severities': selected_names,
            'group_by': group_by,
            'hide_events_table': not show_events_table,
            'info': None if grouped else 'Nenhum chamado encontrado.'
        })
