import pandas as pd
from .base_collector import BaseCollector


class SlaIncidentsTableCollector(BaseCollector):
    """
    SLA (Tabela) calculado a partir dos incidentes (PROBLEM→OK) do período.
    - Coleta todos os eventos dos hosts do cliente, filtra PROBLEM e correlaciona com OK.
    - Soma a duração por host e computa SLA = 100 * (1 - downtime/total_periodo).
    - Filtros suportados (custom_options):
        host_contains: substring (case-insensitive) para filtrar hosts considerados
        problem_contains: substring (case-insensitive) para filtrar somente incidentes cujo nome contenha a substring
        decimals: casas decimais (default 2)
        sort_by: uma das ['SLA (%)','Host','Downtime (s)']
        sort_asc: bool (default True)
        top_n: int (0 = todos)
        show_downtime: bool (default True)
        show_goal: bool (default False)
        target_sla: float opcional
    """

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {}) or {}
        host_contains = (o.get('host_contains') or '').strip()
        problem_contains = (o.get('problem_contains') or '').strip()
        decimals = int(o.get('decimals', 2) or 2)
        sort_by = o.get('sort_by') or 'SLA (%)'
        sort_asc = bool(o.get('sort_asc', True))
        top_n = int(o.get('top_n', 0) or 0)
        show_downtime = bool(o.get('show_downtime', True))
        show_goal = bool(o.get('show_goal', False))
        target_sla = o.get('target_sla')
        try:
            target_sla = float(target_sla) if target_sla not in (None, '') else None
        except Exception:
            target_sla = None

        # Coleta de eventos para todos os hosts
        all_host_ids = [h['hostid'] for h in all_hosts]
        events = self.generator.obter_eventos_wrapper(all_host_ids, period, 'hostids')
        if events is None:
            return self.render('sla_incidents_table', {'summary_html': '', 'table_html': '<p><i>Falha ao coletar eventos.</i></p>'})

        # Filtra problemas
        problems_only = [p for p in (events or []) if str(p.get('source')) == '0' and str(p.get('object')) == '0' and str(p.get('value')) == '1']
        # Filtro por severidade (opcional)
        sev_map = {'info': '1', 'warning': '2', 'average': '3', 'high': '4', 'disaster': '5', 'not_classified': '0'}
        severities = o.get('severities')
        if isinstance(severities, list) and len(severities) > 0:
            allowed = {sev_map.get(s) for s in severities if sev_map.get(s) is not None}
            problems_only = [p for p in problems_only if str(p.get('severity')) in allowed]

        # Opcional: filtro de problema por substring
        if problem_contains:
            pc = problem_contains.lower()
            problems_only = [p for p in problems_only if pc in str(p.get('name','')).lower()]

        if not problems_only:
            return self.render('sla_incidents_table', {'summary_html': '', 'table_html': '<p><i>Nenhum incidente no período/filtros.</i></p>'})

        # Correlação PROBLEM→OK (usa o núcleo do ReportGenerator)
        correlated = self.generator._correlate_problems(problems_only, events, period)

        # Soma downtime por host (união de intervalos para evitar dupla contagem)
        p_start = int(period['start']); p_end = int(period['end'])
        total_seconds = max(1, p_end - p_start)
        host_map = {str(h['hostid']): h['nome_visivel'] for h in (all_hosts or [])}

        def _accept_host(hname: str) -> bool:
            if not host_contains:
                return True
            try:
                return host_contains.lower() in str(hname).lower()
            except Exception:
                return True

        intervals_by_host = {}
        for pr in (correlated or []):
            hid = str(pr.get('hostid')) if pr.get('hostid') is not None else None
            if not hid:
                continue
            hname = host_map.get(hid, f'Host {hid}')
            if not _accept_host(hname):
                continue
            try:
                s = max(p_start, int(pr.get('start', p_start)))
                e = min(p_end, int(pr.get('end', p_end)))
            except Exception:
                continue
            if e <= s:
                continue
            intervals_by_host.setdefault(hname, []).append((s, e))

        downtime = {}
        for hname, ivals in intervals_by_host.items():
            ivals.sort(key=lambda x: x[0])
            cur_s, cur_e = ivals[0]
            merged_total = 0
            for s, e in ivals[1:]:
                if s <= cur_e:
                    if e > cur_e:
                        cur_e = e
                else:
                    merged_total += (cur_e - cur_s)
                    cur_s, cur_e = s, e
            merged_total += (cur_e - cur_s)
            downtime[hname] = merged_total

        if not downtime:
            return self.render('sla_incidents_table', {'summary_html': '', 'table_html': '<p><i>Nenhum downtime pelos filtros aplicados.</i></p>'})

        # Monta DataFrame com SLA por host
        rows = []
        for hname, d in downtime.items():
            sla = max(0.0, min(100.0, 100.0 * (1.0 - (float(d) / float(total_seconds)))))
            rows.append({'Host': hname, 'Downtime (s)': int(d), 'SLA (%)': float(sla)})
        df = pd.DataFrame(rows)

        # Ordenação, top N e formatação
        if sort_by in df.columns:
            try:
                df = df.sort_values(by=sort_by, ascending=sort_asc)
            except Exception:
                pass
        if top_n > 0:
            df = df.head(top_n)

        # Formatação de decimais e meta
        df_disp = df.copy()
        try:
            df_disp['SLA (%)'] = df_disp['SLA (%)'].map(lambda v: f"{v:.{decimals}f}".replace('.', ','))
        except Exception:
            pass
        if show_downtime:
            # Apresentar Downtime (s) também em HH:MM:SS na tabela
            def _fmt_hms(s):
                try:
                    s = int(s)
                    h = s // 3600; s %= 3600; m = s // 60; s %= 60
                    return f"{h:02d}:{m:02d}:{s:02d}"
                except Exception:
                    return "00:00:00"
            df_disp['Tempo Indisponível'] = df_disp['Downtime (s)'].apply(_fmt_hms)
        else:
            if 'Downtime (s)' in df_disp.columns:
                df_disp = df_disp.drop(columns=['Downtime (s)'])
        if show_goal and target_sla is not None:
            try:
                df_disp['Meta'] = df['SLA (%)'].apply(lambda x: 'Atingido' if float(x) >= float(target_sla) else 'Não Atingido')
            except Exception:
                pass

        # Monta HTML simples
        header = ''.join(f"<th>{c}</th>" for c in df_disp.columns)
        body_rows = []
        for _, r in df_disp.iterrows():
            tds = ''.join(f"<td>{r[c]}</td>" for c in df_disp.columns)
            body_rows.append(f"<tr>{tds}</tr>")
        table_html = f"<table class='table'><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"

        return self.render('sla_incidents_table', {'summary_html': '', 'table_html': table_html})
