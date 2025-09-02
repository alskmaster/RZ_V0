import pandas as pd
from .base_collector import BaseCollector


class SlaTableCollector(BaseCollector):
    """
    Renderiza a tabela de Análise de SLA (Disponibilidade) com opções de customização.
    Reaproveita os dados já processados pelo ReportGenerator (availability_data_cache).
    """

    def collect(self, all_hosts, period, availability_data, df_prev_month=None):
        self._update_status("Montando Tabela de SLA...")

        df_sla = availability_data.get('df_sla_problems', pd.DataFrame()).copy()
        if df_sla.empty:
            return self.render('sla_table', {'summary_html': '', 'table_html': '<p><i>Nenhum dado de disponibilidade.</i></p>'})

        opts = self.module_config.get('custom_options', {}) or {}
        sla_goal = self.generator.client.sla_contract
        try:
            override_goal = opts.get('target_sla')
            if override_goal is not None and str(override_goal).strip() != '':
                sla_goal = float(override_goal)
        except Exception:
            pass

        cols = ['Host']
        if opts.get('show_ip') and 'IP' in df_sla.columns:
            cols.append('IP')

        current_sla_col = 'SLA (%)'
        if opts.get('compare_to_previous_month') and df_prev_month is not None and not df_prev_month.empty:
            prev = df_prev_month[['Host', 'SLA_anterior']]
            df_sla = df_sla.merge(prev, on='Host', how='left').fillna({'SLA_anterior': 100.0})
            df_sla.rename(columns={'SLA (%)': 'SLA Atual (%)'}, inplace=True)
            current_sla_col = 'SLA Atual (%)'
            if opts.get('show_previous_sla'):
                cols.append('SLA_anterior')
            if opts.get('show_improvement'):
                df_sla['Melhoria/Piora'] = df_sla[current_sla_col] - df_sla['SLA_anterior']
                cols.append('Melhoria/Piora')

        cols.append(current_sla_col)
        if opts.get('show_downtime') and 'Tempo Indisponível' in df_sla.columns:
            cols.append('Tempo Indisponível')

        if opts.get('show_goal'):
            df_sla['Meta'] = df_sla[current_sla_col].apply(lambda x: "Atingido" if x >= sla_goal else "Não Atingido")
            cols.append('Meta')

        # Sorting/top
        sort_by = opts.get('sort_by') or current_sla_col
        sort_dir = bool(opts.get('sort_asc', False))
        top_n = int(opts.get('top_n', 0) or 0)
        try:
            if sort_by in df_sla.columns:
                df_sla = df_sla.sort_values(by=sort_by, ascending=sort_dir)
        except Exception:
            pass
        if top_n > 0:
            df_sla = df_sla.head(top_n)

        # Summary
        failed = df_sla[df_sla[current_sla_col] < 100].shape[0] if current_sla_col in df_sla.columns else 0
        total_hosts = len(self.generator.cached_data.get('all_hosts', []))
        summary_html = ''
        if not opts.get('hide_summary'):
            alert_class = 'alert-success' if failed == 0 else 'alert-warning'
            summary_html = (
                f'<div class="alert {alert_class} mt-3" role="alert">'
                f'<p>Atenção: {failed} de {total_hosts} hosts analisados não atingiram 100% de disponibilidade.</p>'
                f'</div>'
            )

        # Build minimal HTML table (com destaque opcional abaixo da meta)
        display = [c for c in cols if c in df_sla.columns]
        df_disp = df_sla[display].copy()
        decimals = int(opts.get('decimals', 2) or 2)
        highlight = bool(opts.get('highlight_below_goal', False))
        for c in df_disp.columns:
            if df_disp[c].dtype == float:
                df_disp[c] = df_disp[c].map(lambda v: (f"{v:.{decimals}f}".replace('.', ',') if pd.notna(v) else ''))
        if highlight and current_sla_col in df_sla.columns:
            rows = []
            for _, row in df_disp.iterrows():
                style = ''
                try:
                    val = float(str(row[current_sla_col]).replace(',', '.'))
                    if val < float(sla_goal):
                        style = ' style="background-color:#fff3cd;"'
                except Exception:
                    pass
                tds = ''.join(f"<td>{row[c]}</td>" for c in df_disp.columns)
                rows.append(f"<tr{style}>" + tds + "</tr>")
            header = ''.join(f"<th>{c}</th>" for c in df_disp.columns)
            table_html = f"<table class='table'><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
        else:
            table_html = df_disp.to_html(classes='table', index=False, escape=False)

        return self.render('sla_table', {'summary_html': summary_html, 'table_html': table_html})
