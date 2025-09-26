from .base_collector import BaseCollector
import datetime as dt
import pandas as pd


class IncidentAvailabilityCollector(BaseCollector):
    """Consolida incidentes para calcular disponibilidade agregada."""

    _DEFAULT_SEVERITIES = ['info', 'warning', 'average', 'high', 'disaster']
    _SEVERITY_FILTER_MAP = {
        'not_classified': '0',
        'info': '1',
        'warning': '2',
        'average': '3',
        'high': '4',
        'disaster': '5',
    }
    _SEVERITY_LABELS = {
        '0': 'Nao classificado',
        '1': 'Informacao',
        '2': 'Atencao',
        '3': 'Media',
        '4': 'Alta',
        '5': 'Desastre',
    }

    def _resolve_period(self, base_period, preset):
        try:
            now = int(dt.datetime.now().timestamp())
            end = int(base_period.get('end', now))
        except Exception:
            now = int(dt.datetime.now().timestamp())
            end = now
        if preset == 'last_24h':
            start = max(0, end - 24 * 3600)
        elif preset == 'last_7d':
            start = max(0, end - 7 * 24 * 3600)
        else:
            try:
                end_dt = dt.datetime.fromtimestamp(end)
                first_day = end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if first_day.month == 12:
                    next_month = first_day.replace(year=first_day.year + 1, month=1)
                else:
                    next_month = first_day.replace(month=first_day.month + 1)
                computed_end = int((next_month - dt.timedelta(seconds=1)).timestamp())
                start = int(first_day.timestamp())
                end = min(computed_end, now)
                if end <= start:
                    end = min(int(base_period.get('end', start + 1)), start + 1)
            except Exception:
                start = max(0, end - 30 * 24 * 3600)
        if end <= start:
            end = start + 1
        return {'start': start, 'end': end}

    def _format_duration(self, seconds):
        try:
            seconds = int(seconds)
        except Exception:
            return '0s'
        if seconds <= 0:
            return '0s'
        parts = []
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, sec = divmod(rem, 60)
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if sec and not parts:
            parts.append(f"{sec}s")
        return ' '.join(parts) or '0s'

    def _format_timestamp(self, ts):
        try:
            return dt.datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            return 'N/A'

    def _merge_intervals(self, intervals):
        norm = []
        for st, en in intervals:
            try:
                st = int(st)
                en = int(en)
            except Exception:
                continue
            if en < st:
                en = st
            norm.append((st, en))
        if not norm:
            return [], 0
        norm.sort(key=lambda x: x[0])
        merged = [list(norm[0])]
        for st, en in norm[1:]:
            last = merged[-1]
            if st <= last[1]:
                last[1] = max(last[1], en)
            else:
                merged.append([st, en])
        total = sum(max(0, en - st) for st, en in merged)
        return [(st, en) for st, en in merged], total

    def _parse_float(self, value):
        if value is None:
            return None
        try:
            raw = str(value).strip().replace('%', '').replace(',', '.').replace(' ', '')
            if raw == '':
                return None
            return float(raw)
        except Exception:
            return None

    def _tokenize(self, value):
        if not value:
            return []
        return [token.strip() for token in str(value).split(',') if token.strip()]

    def collect(self, all_hosts, period):
        opts = self.module_config.get('custom_options', {}) or {}
        severities = opts.get('severities') or list(self._DEFAULT_SEVERITIES)
        severity_ids = [self._SEVERITY_FILTER_MAP[s] for s in severities if s in self._SEVERITY_FILTER_MAP]
        if not severity_ids:
            severity_ids = [self._SEVERITY_FILTER_MAP[s] for s in self._DEFAULT_SEVERITIES]
        period_mode = opts.get('period_mode') or 'full_month'
        host_filter = (opts.get('host_contains') or '').strip()
        host_exclude = (opts.get('host_exclude') or '').strip()
        problem_filter = (opts.get('problem_contains') or '').strip()
        problem_exclude = (opts.get('problem_exclude') or '').strip()
        tags_include = (opts.get('tags_include') or '').strip()
        tags_exclude = (opts.get('tags_exclude') or '').strip()
        group_by = (opts.get('group_by') or 'host').lower()
        top_n_raw = opts.get('top_n_hosts')
        show_duration = bool(opts.get('show_duration', True))
        show_acknowledgements = bool(opts.get('show_acknowledgements', False))
        show_details = bool(opts.get('show_details', False))
        ack_filter = (opts.get('ack_filter') or 'all').lower()
        target_availability = self._parse_float(opts.get('target_availability'))
        show_insight = bool(opts.get('show_insight', True))

        effective_period = self._resolve_period(period, period_mode)
        period_seconds = max(1, effective_period['end'] - effective_period['start'])

        host_map = {}
        all_host_ids = []
        for h in (all_hosts or []):
            hid = str(h.get('hostid'))
            if hid:
                host_map[hid] = h.get('nome_visivel') or h.get('name') or f'Host {hid}'
                all_host_ids.append(hid)
        total_hosts = len(all_host_ids)

        if not all_host_ids:
            return self.render('incident_availability', {
                'error': 'Nenhum host disponivel para analise. Verifique o escopo do cliente.'
            })

        events = self.generator.obter_eventos_wrapper(all_host_ids, effective_period, 'hostids')
        if events is None:
            return self.render('incident_availability', {
                'error': 'Falha ao coletar incidentes no periodo selecionado.'
            })

        problem_events = [ev for ev in (events or [])
                          if str(ev.get('value')) == '1' and str(ev.get('source')) == '0' and str(ev.get('object')) == '0']
        monitored_trigger_ids = {str(ev.get('objectid') or ev.get('triggerid') or '') for ev in problem_events}
        raw_incident_total = len(problem_events)

        df = pd.DataFrame(problem_events)
        if df.empty:
            return self.render('incident_availability', self._render_payload(
                opts_context={
                    'group_by': group_by,
                    'show_duration': show_duration,
                    'show_acknowledgements': show_acknowledgements,
                    'show_details': show_details,
                    'severity_ids': severity_ids,
                    'period_mode': period_mode,
                    'ack_filter': ack_filter,
                },
                summary_context={
                    'period': effective_period,
                    'period_seconds': period_seconds,
                    'total_incidents': 0,
                    'downtime_seconds': 0,
                    'host_count': total_hosts,
                    'hosts_with_incidents': 0,
                    'trigger_count': len(monitored_trigger_ids),
                    'raw_incidents': raw_incident_total,
                    'filtered_incidents': 0,
                    'severity_ids': severity_ids,
                    'ack_counts': {'with_ack': 0, 'without_ack': 0},
                    'target_availability': target_availability,
                    'insight': 'Nenhum incidente encontrado. Ambiente 100% disponivel.',
                },
                groups=[],
                details=[],
                filters=self._build_filters(severities, host_filter, host_exclude,
                                            problem_filter, problem_exclude,
                                            tags_include, tags_exclude, ack_filter),
                coverage={'monitored_triggers': len(monitored_trigger_ids), 'raw_incidents': raw_incident_total}
            ))

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
            return self.render('incident_availability', self._render_payload(
                opts_context={
                    'group_by': group_by,
                    'show_duration': show_duration,
                    'show_acknowledgements': show_acknowledgements,
                    'show_details': show_details,
                    'severity_ids': severity_ids,
                    'period_mode': period_mode,
                    'ack_filter': ack_filter,
                },
                summary_context={
                    'period': effective_period,
                    'period_seconds': period_seconds,
                    'total_incidents': 0,
                    'downtime_seconds': 0,
                    'host_count': total_hosts,
                    'hosts_with_incidents': 0,
                    'trigger_count': len(monitored_trigger_ids),
                    'raw_incidents': raw_incident_total,
                    'filtered_incidents': raw_incident_total,
                    'severity_ids': severity_ids,
                    'ack_counts': {'with_ack': 0, 'without_ack': 0},
                    'target_availability': target_availability,
                    'insight': 'Nenhum incidente com as severidades selecionadas.',
                },
                groups=[],
                details=[],
                filters=self._build_filters(severities, host_filter, host_exclude,
                                            problem_filter, problem_exclude,
                                            tags_include, tags_exclude, ack_filter),
                coverage={'monitored_triggers': len(monitored_trigger_ids), 'raw_incidents': raw_incident_total}
            ))

        df['acknowledged'] = df.get('acknowledged', 0).astype(str)
        if ack_filter in ('only_acked', 'only_unacked'):
            flag = '1' if ack_filter == 'only_acked' else '0'
            df = df[df['acknowledged'] == flag]
        if df.empty:
            return self.render('incident_availability', self._render_payload(
                opts_context={
                    'group_by': group_by,
                    'show_duration': show_duration,
                    'show_acknowledgements': show_acknowledgements,
                    'show_details': show_details,
                    'severity_ids': severity_ids,
                    'period_mode': period_mode,
                    'ack_filter': ack_filter,
                },
                summary_context={
                    'period': effective_period,
                    'period_seconds': period_seconds,
                    'total_incidents': 0,
                    'downtime_seconds': 0,
                    'host_count': total_hosts,
                    'hosts_with_incidents': 0,
                    'trigger_count': len(monitored_trigger_ids),
                    'raw_incidents': raw_incident_total,
                    'filtered_incidents': raw_incident_total,
                    'severity_ids': severity_ids,
                    'ack_counts': {'with_ack': 0, 'without_ack': 0},
                    'target_availability': target_availability,
                    'insight': 'Incidentes existiram, porem foram filtrados pelo criterio de reconhecimento.',
                },
                groups=[],
                details=[],
                filters=self._build_filters(severities, host_filter, host_exclude,
                                            problem_filter, problem_exclude,
                                            tags_include, tags_exclude, ack_filter),
                coverage={'monitored_triggers': len(monitored_trigger_ids), 'raw_incidents': raw_incident_total}
            ))

        df['hostid'] = df.get('hosts').apply(
            lambda lst: str(lst[0].get('hostid')) if isinstance(lst, list) and lst and isinstance(lst[0], dict) and lst[0].get('hostid') else None
        )
        df['host_name'] = df['hostid'].map(lambda hid: host_map.get(str(hid), f'Host {hid}'))

        inc_tokens = [t.lower() for t in self._tokenize(host_filter)]
        exc_tokens = [t.lower() for t in self._tokenize(host_exclude)]
        if inc_tokens:
            df = df[df['host_name'].astype(str).str.lower().apply(lambda name: any(tok in name for tok in inc_tokens))]
        if exc_tokens:
            df = df[~df['host_name'].astype(str).str.lower().apply(lambda name: any(tok in name for tok in exc_tokens))]
        if df.empty:
            return self.render('incident_availability', self._render_payload(
                opts_context={
                    'group_by': group_by,
                    'show_duration': show_duration,
                    'show_acknowledgements': show_acknowledgements,
                    'show_details': show_details,
                    'severity_ids': severity_ids,
                    'period_mode': period_mode,
                    'ack_filter': ack_filter,
                },
                summary_context={
                    'period': effective_period,
                    'period_seconds': period_seconds,
                    'total_incidents': 0,
                    'downtime_seconds': 0,
                    'host_count': total_hosts,
                    'hosts_with_incidents': 0,
                    'trigger_count': len(monitored_trigger_ids),
                    'raw_incidents': raw_incident_total,
                    'filtered_incidents': raw_incident_total,
                    'severity_ids': severity_ids,
                    'ack_counts': {'with_ack': 0, 'without_ack': 0},
                    'target_availability': target_availability,
                    'insight': 'Nenhum host restante apos aplicar os filtros.',
                },
                groups=[],
                details=[],
                filters=self._build_filters(severities, host_filter, host_exclude,
                                            problem_filter, problem_exclude,
                                            tags_include, tags_exclude, ack_filter),
                coverage={'monitored_triggers': len(monitored_trigger_ids), 'raw_incidents': raw_incident_total}
            ))

        prob_inc = self._tokenize(problem_filter)
        if prob_inc:
            for tok in prob_inc:
                df = df[df['name'].astype(str).str.contains(tok, case=False, na=False)]
        prob_exc = [t.lower() for t in self._tokenize(problem_exclude)]
        if prob_exc:
            df = df[~df['name'].astype(str).str.lower().apply(lambda nm: any(tok in nm for tok in prob_exc))]
        if df.empty:
            return self.render('incident_availability', self._render_payload(
                opts_context={
                    'group_by': group_by,
                    'show_duration': show_duration,
                    'show_acknowledgements': show_acknowledgements,
                    'show_details': show_details,
                    'severity_ids': severity_ids,
                    'period_mode': period_mode,
                    'ack_filter': ack_filter,
                },
                summary_context={
                    'period': effective_period,
                    'period_seconds': period_seconds,
                    'total_incidents': 0,
                    'downtime_seconds': 0,
                    'host_count': total_hosts,
                    'hosts_with_incidents': 0,
                    'trigger_count': len(monitored_trigger_ids),
                    'raw_incidents': raw_incident_total,
                    'filtered_incidents': raw_incident_total,
                    'severity_ids': severity_ids,
                    'ack_counts': {'with_ack': 0, 'without_ack': 0},
                    'target_availability': target_availability,
                    'insight': 'Nenhum incidente restante apos aplicar filtros de problema.',
                },
                groups=[],
                details=[],
                filters=self._build_filters(severities, host_filter, host_exclude,
                                            problem_filter, problem_exclude,
                                            tags_include, tags_exclude, ack_filter),
                coverage={'monitored_triggers': len(monitored_trigger_ids), 'raw_incidents': raw_incident_total}
            ))

        need_tags = bool(tags_include or tags_exclude)
        if need_tags:
            try:
                tags_map = self.generator.obter_eventos_tags_details(df['eventid'].tolist()) or {}
            except Exception:
                tags_map = {}
            df['tags_raw'] = df['eventid'].astype(str).map(lambda eid: tags_map.get(str(eid), []))
            df['_tag_tokens'] = df['tags_raw'].apply(lambda lst: [
                f"{str(tag.get('tag','')).lower()}={str(tag.get('value','')).lower()}" for tag in (lst or []) if isinstance(tag, dict)
            ] + [str(tag.get('tag','')).lower() for tag in (lst or []) if isinstance(tag, dict)]
                                  + [str(tag.get('value','')).lower() for tag in (lst or []) if isinstance(tag, dict)])
            inc_tag_tokens = [t.lower() for t in self._tokenize(tags_include)]
            exc_tag_tokens = [t.lower() for t in self._tokenize(tags_exclude)]
            if inc_tag_tokens:
                df = df[df['_tag_tokens'].apply(lambda toks: any(any(it in token for token in toks) for it in inc_tag_tokens))]
            if exc_tag_tokens:
                df = df[~df['_tag_tokens'].apply(lambda toks: any(any(et in token for token in toks) for et in exc_tag_tokens))]
            if df.empty:
                return self.render('incident_availability', self._render_payload(
                    opts_context={
                        'group_by': group_by,
                        'show_duration': show_duration,
                        'show_acknowledgements': show_acknowledgements,
                        'show_details': show_details,
                        'severity_ids': severity_ids,
                        'period_mode': period_mode,
                        'ack_filter': ack_filter,
                    },
                    summary_context={
                        'period': effective_period,
                        'period_seconds': period_seconds,
                        'total_incidents': 0,
                        'downtime_seconds': 0,
                        'host_count': total_hosts,
                        'hosts_with_incidents': 0,
                        'trigger_count': len(monitored_trigger_ids),
                        'raw_incidents': raw_incident_total,
                        'filtered_incidents': raw_incident_total,
                        'severity_ids': severity_ids,
                        'ack_counts': {'with_ack': 0, 'without_ack': 0},
                        'target_availability': target_availability,
                        'insight': 'Nenhum incidente restante apos filtros de tags.',
                    },
                    groups=[],
                    details=[],
                    filters=self._build_filters(severities, host_filter, host_exclude,
                                                problem_filter, problem_exclude,
                                                tags_include, tags_exclude, ack_filter),
                    coverage={'monitored_triggers': len(monitored_trigger_ids), 'raw_incidents': raw_incident_total}
                ))

        problem_records = df.to_dict('records')
        correlated = self.generator._correlate_problems(problem_records, events, effective_period) or []
        correlated_map = {str(item.get('eventid')): item for item in correlated if item.get('eventid') is not None}

        df['start_ts'] = df['clock'].astype(int)
        df['eventid'] = df['eventid'].astype(str)
        df['end_ts'] = df['eventid'].map(lambda eid: int(correlated_map.get(eid, {}).get('end', effective_period['end'])))
        df['end_ts'] = df.apply(lambda row: row['start_ts'] if row['end_ts'] < row['start_ts'] else row['end_ts'], axis=1)
        df['duration_seconds'] = (df['end_ts'] - df['start_ts']).clip(lower=0)
        df['duration_human'] = df['duration_seconds'].apply(self._format_duration)
        df['severity_label'] = df['severity'].map(self._SEVERITY_LABELS).fillna('Desconhecida')

        ack_map = {}
        need_ack_details = show_acknowledgements or ack_filter == 'only_acked'
        if need_ack_details:
            try:
                ack_map = self.generator.obter_eventos_ack_details(df['eventid'].tolist()) or {}
            except Exception:
                ack_map = {}
        df['ack_details'] = df['eventid'].map(lambda eid: ack_map.get(str(eid), []))
        df['ack_count'] = df['ack_details'].apply(lambda lst: len(lst) if isinstance(lst, list) else 0)

        df['triggerid'] = df.apply(lambda row: str(row.get('objectid') or row.get('triggerid') or ''), axis=1)

        top_n = None
        try:
            if top_n_raw not in (None, ''):
                parsed_top = int(str(top_n_raw).strip())
                if parsed_top > 0:
                    top_n = parsed_top
        except Exception:
            top_n = None

        details = []
        if show_details:
            for _, row in df.sort_values('start_ts').iterrows():
                detail = {
                    'eventid': row['eventid'],
                    'host_name': row['host_name'],
                    'trigger': str(row['name']),
                    'severity': row['severity_label'],
                    'start': self._format_timestamp(row['start_ts']),
                    'end': self._format_timestamp(row['end_ts']),
                    'duration_human': row['duration_human'],
                    'ack_count': row['ack_count'],
                    'ack_details': [
                        {
                            'alias': ack.get('alias'),
                            'message': ack.get('message'),
                            'clock': self._format_timestamp(ack.get('clock')),
                        }
                        for ack in (row['ack_details'] or []) if isinstance(ack, dict)
                    ] if show_acknowledgements else [],
                }
                details.append(detail)

        groups = []
        if group_by == 'host':
            for hid, chunk in df.groupby('hostid'):
                intervals = list(zip(chunk['start_ts'], chunk['end_ts']))
                merged, downtime = self._merge_intervals(intervals)
                availability = None
                if period_seconds > 0:
                    availability = max(0.0, min(100.0, 100.0 * (1 - (downtime / period_seconds))))
                groups.append({
                    'key': str(hid),
                    'label': host_map.get(str(hid), f'Host {hid}'),
                    'incidents': int(len(chunk)),
                    'downtime_seconds': int(downtime),
                    'downtime_human': self._format_duration(downtime),
                    'availability_pct': round(availability, 3) if availability is not None else None,
                    'ack_count': int(chunk['ack_count'].sum()),
                })
            groups.sort(key=lambda item: item['downtime_seconds'], reverse=True)
            if top_n:
                groups = groups[:top_n]
        else:
            for trig, chunk in df.groupby('triggerid'):
                downtime = int(chunk['duration_seconds'].sum())
                impact = None
                if period_seconds > 0:
                    impact = max(0.0, min(100.0, 100.0 * (downtime / period_seconds)))
                groups.append({
                    'key': str(trig or '0'),
                    'label': str(chunk['name'].iloc[0]) if not chunk['name'].empty else f'Trigger {trig}',
                    'host_label': chunk['host_name'].iloc[0] if not chunk['host_name'].empty else 'N/A',
                    'incidents': int(len(chunk)),
                    'downtime_seconds': downtime,
                    'downtime_human': self._format_duration(downtime),
                    'impact_pct': round(impact, 3) if impact is not None else None,
                    'ack_count': int(chunk['ack_count'].sum()),
                })
            groups.sort(key=lambda item: item['downtime_seconds'], reverse=True)

        total_downtime = int(df['duration_seconds'].sum())
        hosts_with_incidents = len(df['hostid'].dropna().unique())
        trigger_count = len(df['triggerid'].dropna().unique())
        ack_counts = {
            'with_ack': int((df['acknowledged'] == '1').sum()),
            'without_ack': int((df['acknowledged'] != '1').sum()),
        }
        severity_breakdown = {
            self._SEVERITY_LABELS.get(code, code): int((df['severity'] == code).sum())
            for code in severity_ids
        }

        availability_pct = None
        if total_hosts > 0 and period_seconds > 0:
            theoretical = period_seconds * total_hosts
            availability_pct = max(0.0, min(100.0, 100.0 * (1 - (total_downtime / theoretical))))

        insight = None
        if show_insight:
            if df.empty:
                insight = 'Nenhum incidente apos filtros: ambiente permaneceu disponivel.'
            elif groups:
                worst = groups[0]
                if group_by == 'host':
                    insight = f"Maior impacto em {worst['label']}: {worst['incidents']} incidente(s), {worst['downtime_human']} indisponiveis."
                else:
                    insight = f"Problema mais impactante: {worst['label']} ({worst['downtime_human']} de impacto)."
            if availability_pct is not None and target_availability is not None:
                status = 'atingiu' if availability_pct >= target_availability else 'nao atingiu'
                part = f"Disponibilidade {status} a meta de {target_availability:.2f}%."
                insight = f"{insight} {part}" if insight else part

        summary_context = {
            'period': effective_period,
            'period_seconds': period_seconds,
            'total_incidents': int(len(df)),
            'downtime_seconds': total_downtime,
            'host_count': total_hosts,
            'hosts_with_incidents': hosts_with_incidents,
            'trigger_count': trigger_count,
            'raw_incidents': raw_incident_total,
            'filtered_incidents': raw_incident_total - int(len(df)),
            'severity_ids': severity_ids,
            'severity_breakdown': severity_breakdown,
            'ack_counts': ack_counts,
            'availability_pct': availability_pct,
            'target_availability': target_availability,
            'insight': insight,
        }

        payload = self._render_payload(
            opts_context={
                'group_by': group_by,
                'show_duration': show_duration,
                'show_acknowledgements': show_acknowledgements,
                'show_details': show_details,
                'severity_ids': severity_ids,
                'period_mode': period_mode,
                'ack_filter': ack_filter,
            },
            summary_context=summary_context,
            groups=groups,
            details=details,
            filters=self._build_filters(severities, host_filter, host_exclude,
                                        problem_filter, problem_exclude,
                                        tags_include, tags_exclude, ack_filter),
            coverage={'monitored_triggers': len(monitored_trigger_ids), 'raw_incidents': raw_incident_total}
        )
        return self.render('incident_availability', payload)

    def _build_filters(self, severities, host_filter, host_exclude,
                       problem_filter, problem_exclude, tags_include, tags_exclude, ack_filter):
        filters = []
        if severities:
            filters.append({'label': 'Severidades', 'value': ', '.join(severities)})
        if host_filter:
            filters.append({'label': 'Hosts contendo', 'value': host_filter})
        if host_exclude:
            filters.append({'label': 'Hosts excluidos', 'value': host_exclude})
        if problem_filter:
            filters.append({'label': 'Problemas contendo', 'value': problem_filter})
        if problem_exclude:
            filters.append({'label': 'Problemas excluidos', 'value': problem_exclude})
        if tags_include:
            filters.append({'label': 'Tags contendo', 'value': tags_include})
        if tags_exclude:
            filters.append({'label': 'Tags excluidas', 'value': tags_exclude})
        if ack_filter in ('only_acked', 'only_unacked'):
            label = 'Apenas com ACK' if ack_filter == 'only_acked' else 'Apenas sem ACK'
            filters.append({'label': 'Filtro de ACK', 'value': label})
        return filters

    def _render_payload(self, opts_context, summary_context, groups, details, filters, coverage):
        period = summary_context['period']
        period_seconds = summary_context['period_seconds']
        downtime_seconds = summary_context['downtime_seconds']
        availability_pct = summary_context.get('availability_pct')
        if availability_pct is None:
            if summary_context['host_count'] > 0:
                theoretical = period_seconds * summary_context['host_count']
                availability_pct = 100.0 if theoretical == 0 else max(0.0, min(100.0, 100.0 * (1 - (downtime_seconds / theoretical))))
            else:
                availability_pct = 0.0
        payload = {
            'summary': {
                'period_label': f"{self._format_timestamp(period['start'])} - {self._format_timestamp(period['end'])}",
                'period_duration_human': self._format_duration(period_seconds),
                'total_incidents': summary_context['total_incidents'],
                'total_downtime_seconds': downtime_seconds,
                'total_downtime_human': self._format_duration(downtime_seconds),
                'availability_pct': round(availability_pct, 3),
                'hosts_monitored': summary_context['host_count'],
                'hosts_with_incidents': summary_context['hosts_with_incidents'],
                'triggers_with_incidents': summary_context['trigger_count'],
                'raw_incidents': summary_context['raw_incidents'],
                'filtered_incidents': max(0, summary_context['filtered_incidents']),
                'severity_breakdown': summary_context.get('severity_breakdown', {}),
                'ack_counts': summary_context['ack_counts'],
                'target_availability': summary_context.get('target_availability'),
                'target_met': None,
                'insight': summary_context.get('insight'),
            },
            'group_by': opts_context['group_by'],
            'groups': groups,
            'show_duration': opts_context['show_duration'],
            'show_acknowledgements': opts_context['show_acknowledgements'],
            'show_details': opts_context['show_details'],
            'details': details,
            'severity_labels': [self._SEVERITY_LABELS.get(code, code) for code in opts_context['severity_ids']],
            'period_mode': opts_context['period_mode'],
            'ack_filter': opts_context['ack_filter'],
            'filters': filters,
            'coverage': coverage,
        }
        target = summary_context.get('target_availability')
        if target is not None:
            payload['summary']['target_met'] = availability_pct >= target
        return payload