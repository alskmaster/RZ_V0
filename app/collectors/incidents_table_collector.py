from .base_collector import BaseCollector
import datetime
import pandas as pd


class IncidentsTableCollector(BaseCollector):
    """
    Módulo Incidentes (Tabela): apenas informações tabulares, sem gráficos.
    - Filtros por severidade, sub-período e nome do host.
    - Agrupamento por host ou por problema.
    - Campos opcionais: duração e acknowledgements.
    - Suporte a filtros adicionais: ACK, tags, exclusões de host/problema.
    """

    _SEVERITY_MAP = {
        '0': 'Não Classificado',
        '1': 'Informação',
        '2': 'Atenção',
        '3': 'Média',
        '4': 'Alta',
        '5': 'Desastre'
    }

    _SEVERITY_FILTER_MAP = {
        'info': '1',
        'warning': '2',
        'average': '3',
        'high': '4',
        'disaster': '5',
        'not_classified': '0',
    }

    def _format_timestamp(self, ts):
        if not ts:
            return "N/A"
        try:
            return datetime.datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            return "Inválido"

    def _format_duration(self, seconds):
        if not seconds:
            return "0s"
        try:
            seconds = int(seconds)
            if seconds < 0:
                return "N/A"
            days = seconds // 86400
            seconds %= 86400
            hours = seconds // 3600
            seconds %= 3600
            minutes = seconds // 60
            seconds %= 60
            parts = []
            if days: parts.append(f"{days}d")
            if hours: parts.append(f"{hours}h")
            if minutes: parts.append(f"{minutes}m")
            if seconds or not parts: parts.append(f"{seconds}s")
            return " ".join(parts)
        except Exception:
            return "Inválido"

    def _apply_period_subfilter(self, period, sub):
        start, end = period['start'], period['end']
        if sub == 'last_24h':
            end = int(datetime.datetime.now().timestamp())
            start = end - 24 * 3600
        elif sub == 'last_7d':
            end = int(datetime.datetime.now().timestamp())
            start = end - 7 * 24 * 3600
        return {'start': start, 'end': end}

    def collect(self, all_hosts, period):
        opts = self.module_config.get('custom_options', {})
        selected_names = opts.get('severities', ['info', 'warning', 'average', 'high', 'disaster'])
        selected_ids = [self._SEVERITY_FILTER_MAP[s] for s in selected_names if s in self._SEVERITY_FILTER_MAP]
        primary_grouping = opts.get('primary_grouping', 'host')
        show_duration = opts.get('show_duration', True)
        show_ack = opts.get('show_acknowledgements', True)
        # ACK tri-state (compatível com only_with_acknowledgements)
        ack_filter = (opts.get('ack_filter') or 'all').lower()
        if bool(opts.get('only_with_acknowledgements', False)):
            ack_filter = 'only_acked'
        host_name_contains = (opts.get('host_name_contains') or '').strip()
        exclude_hosts_contains = (opts.get('exclude_hosts_contains') or '').strip()
        problem_contains = (opts.get('problem_contains') or '').strip()
        exclude_problem_contains = (opts.get('exclude_problem_contains') or '').strip()
        tags_include = (opts.get('tags_include') or '').strip()
        tags_exclude = (opts.get('tags_exclude') or '').strip()
        top_n_hosts = opts.get('num_hosts')

        period = self._apply_period_subfilter(period, opts.get('period_sub_filter', 'full_month'))

        all_host_ids = [h['hostid'] for h in all_hosts]
        problems = self.generator.obter_eventos_wrapper(all_host_ids, period, 'hostids')
        if problems is None:
            self._update_status("Erro ao coletar eventos de incidentes (tabela).")
            return self.render('incidents_table', {"error": "Não foi possível coletar dados de incidentes."})

        df = pd.DataFrame(problems)
        if df.empty:
            return self.render('incidents_table', {
                "grouped_data": [],
                "selected_severities": selected_names,
                "show_duration": show_duration,
                "show_acknowledgements": show_ack,
                "primary_grouping": primary_grouping,
            })

        # Filtros essenciais
        for c in ('source', 'object', 'value', 'severity'):
            if c in df.columns:
                df[c] = df[c].astype(str)
        df = df[(df['source'] == '0') & (df['object'] == '0') & (df['value'] == '1')]
        if selected_ids:
            df = df[df['severity'].astype(str).isin(selected_ids)]
        # Filtro por ACK (tri-state)
        if 'acknowledged' in df.columns and ack_filter in ('only_acked', 'only_unacked'):
            flag = '1' if ack_filter == 'only_acked' else '0'
            try:
                df = df[df['acknowledged'].astype(str) == flag]
            except Exception:
                pass
        if df.empty:
            return self.render('incidents_table', {
                "grouped_data": [],
                "selected_severities": selected_names,
                "show_duration": show_duration,
                "show_acknowledgements": show_ack,
                "primary_grouping": primary_grouping,
            })

        # Host visível
        host_name_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}
        df['host_name'] = df['hosts'].apply(lambda x: host_name_map.get(x[0].get('hostid')) if isinstance(x, list) and x and isinstance(x[0], dict) and x[0].get('hostid') else 'Desconhecido')
        if host_name_contains:
            df = df[df['host_name'].str.contains(host_name_contains, case=False, na=False)]
        if exclude_hosts_contains:
            tokens = [t.strip().lower() for t in exclude_hosts_contains.split(',') if t.strip()]
            if tokens:
                df = df[~df['host_name'].astype(str).str.lower().apply(lambda nm: any(t in nm for t in tokens))]
        if problem_contains:
            df = df[df['name'].astype(str).str.contains(problem_contains, case=False, na=False)]
        if exclude_problem_contains:
            tokens_p = [t.strip().lower() for t in exclude_problem_contains.split(',') if t.strip()]
            if tokens_p:
                df = df[~df['name'].astype(str).str.lower().apply(lambda nm: any(t in nm for t in tokens_p))]
        if df.empty:
        # Filtros por tags quando dispon�veis
        if ('tags' in df.columns) and (tags_include or tags_exclude):
            inc = [t.strip().lower() for t in tags_include.split(',') if t.strip()]
            exc = [t.strip().lower() for t in tags_exclude.split(',') if t.strip()]
            def _norm_tags(tlist):
                try:
                    return [ (str((tt.get('tag') if isinstance(tt, dict) else '')) + ':' + str((tt.get('value') if isinstance(tt, dict) else ''))).lower() for tt in (tlist or []) if isinstance(tt, dict) ]
                except Exception:
                    return []
            try:
                df['_tag_strs'] = df['tags'].apply(_norm_tags)
                if inc:
                    df = df[df['_tag_strs'].apply(lambda lst: any(any(i in s for s in lst) for i in inc))]
                if exc:
                    df = df[~df['_tag_strs'].apply(lambda lst: any(any(e in s for s in lst) for e in exc))]
            except Exception:
                pass
            return self.render('incidents_table', {
                "grouped_data": [],
                "selected_severities": selected_names,
                "show_duration": show_duration,
                "show_acknowledgements": show_ack,
                "primary_grouping": primary_grouping,
            })

        # Campos de exibição
        df['severity_name'] = df['severity'].astype(str).map(self._SEVERITY_MAP).fillna('Desconhecido')
        df['formatted_clock'] = df['clock'].apply(self._format_timestamp)
        # Correlação PROBLEM -> OK usando todos os eventos do período (para determinar fim real)
        end_map = {}
        try:
            problems_only = [p for p in (problems or []) if str(p.get('source')) == '0' and str(p.get('object')) == '0' and str(p.get('value')) == '1']
            correlated = self.generator._correlate_problems(problems_only, problems, period)
            end_map = {(str(c.get('triggerid')), int(c.get('start'))): int(c.get('end')) for c in (correlated or []) if c.get('start') is not None}
        except Exception:
            end_map = {}
        # Duração: se houver r_event (OK), usa-o como fim; caso contrário, usa o fim do período do relatório
        try:
            period_end_ts = int(period.get('end'))
        except Exception:
            import time as _t
            period_end_ts = int(_t.time())
        def _end_ts(row):
            # 1) tenta fim correlacionado: chave (triggerid, start_clock)
            try:
                tid = str(row.get('objectid') or row.get('triggerid'))
                st = int(row.get('clock'))
                if (tid, st) in end_map:
                    return int(end_map[(tid, st)])
            except Exception:
                pass
            if isinstance(row.get('r_event'), dict) and row['r_event'].get('clock'):
                try:
                    return int(row['r_event'].get('clock'))
                except Exception:
                    return period_end_ts
            return period_end_ts
        # Garantir numéricos seguros para cálculo
        df['start_ts'] = pd.to_numeric(df['clock'], errors='coerce').fillna(period_end_ts).astype(int)
        df['end_ts'] = df.apply(_end_ts, axis=1)
        df['duration_seconds'] = (df['end_ts'] - df['start_ts']).clip(lower=0)
        df['formatted_duration'] = df['duration_seconds'].apply(self._format_duration)
        df['processed_acknowledgements'] = df['acknowledges'].apply(lambda acks: [
            {
                'alias': ack.get('alias', 'N/A'),
                'message': ack.get('message', 'N/A'),
                'clock': self._format_timestamp(ack.get('clock', 0)),
            }
            for ack in (acks or []) if isinstance(acks, list) and isinstance(ack, dict)
        ])

        # Filtro opcional: exibir apenas incidentes que possuem pelo menos um reconhecimento
        if ack_filter == 'only_acked':
            try:
                df = df[df['processed_acknowledgements'].apply(lambda lst: isinstance(lst, list) and len(lst) > 0)]
            except Exception:
                pass
        if df.empty:
            return self.render('incidents_table', {
                "grouped_data": [],
                "selected_severities": selected_names,
                "show_duration": show_duration,
                "show_acknowledgements": show_ack,
                "primary_grouping": primary_grouping,
            })

        grouped_data = []
        if primary_grouping == 'host':
            if top_n_hosts:
                counts = df.groupby('host_name').size().reset_index(name='incident_count')
                sorted_keys = counts.sort_values(by='incident_count', ascending=False).head(int(top_n_hosts))['host_name'].tolist()
            else:
                sorted_keys = sorted(df['host_name'].dropna().unique().tolist())
            for key in sorted_keys:
                gdf = df[df['host_name'] == key]
                incidents_list = []
                for _, row in gdf.sort_values(by='clock', ascending=False).iterrows():
                    incidents_list.append({
                        'name': row.get('name'),
                        'severity': row.get('severity_name'),
                        'clock': row.get('formatted_clock'),
                        'duration': row.get('formatted_duration'),
                        'acknowledges': row.get('processed_acknowledgements'),
                    })
                grouped_data.append({'primary_key_name': key, 'incidents': incidents_list})
        else:  # problem
            counts = df.groupby('name').size().reset_index(name='incident_count')
            sorted_keys = counts.sort_values(by='incident_count', ascending=False)['name'].tolist()
            for key in sorted_keys:
                gdf = df[df['name'] == key]
                hosts_affected = []
                for host_name, hgroup in gdf.groupby('host_name'):
                    incidents_list = []
                    for _, row in hgroup.sort_values(by='clock', ascending=False).iterrows():
                        incidents_list.append({
                            'name': row.get('name'),
                            'severity': row.get('severity_name'),
                            'clock': row.get('formatted_clock'),
                            'duration': row.get('formatted_duration'),
                            'acknowledges': row.get('processed_acknowledgements'),
                        })
                    hosts_affected.append({'host_name': host_name, 'incidents': incidents_list})
                grouped_data.append({'primary_key_name': key, 'hosts_affected': sorted(hosts_affected, key=lambda x: x['host_name'])})

        return self.render('incidents_table', {
            'grouped_data': grouped_data,
            'selected_severities': selected_names,
            'show_duration': show_duration,
            'show_acknowledgements': show_ack,
            'primary_grouping': primary_grouping,
        })




