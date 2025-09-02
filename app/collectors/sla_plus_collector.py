import pandas as pd
from .base_collector import BaseCollector


class SlaPlusCollector(BaseCollector):
    """
    SLA Plus VIP:
    - KPIs comparativos (mês atual x anterior)
    - Lista de hosts abaixo da meta com gap e delta
    - Top regressões e melhoras por host
    Opções (custom_options):
      - target_sla (float, default: do cliente)
      - top_n (int, default 10)
      - show_cards, show_below_target, show_top_regressions, show_top_improvements (bool)
      - min_delta (float, limiar absoluto para listar em top changes; default 0)
    """

    def collect(self, all_hosts, period, availability_data, df_prev_month=None):
        self._update_status("Montando SLA Plus VIP...")

        opts = self.module_config.get('custom_options', {}) or {}
        try:
            target_sla = float(opts.get('target_sla')) if opts.get('target_sla') is not None else float(self.generator._get_client_sla_contract() or 0)
        except Exception:
            target_sla = None
        top_n = int(opts.get('top_n', 10) or 10)
        show_cards = bool(opts.get('show_cards', True))
        show_below = bool(opts.get('show_below_target', True))
        show_reg = bool(opts.get('show_top_regressions', True))
        show_imp = bool(opts.get('show_top_improvements', False))
        min_delta = float(opts.get('min_delta', 0) or 0)

        df_cur = availability_data.get('df_sla_problems', pd.DataFrame()).copy()
        if df_cur.empty:
            return self.render('sla_plus', {
                'cards': '', 'below_table': '<p><i>Sem dados para o período.</i></p>',
                'reg_table': '', 'imp_table': ''
            })

        # Normaliza tipos
        if 'SLA (%)' in df_cur.columns:
            df_cur['SLA (%)'] = pd.to_numeric(df_cur['SLA (%)'], errors='coerce')
        else:
            # tenta detectar coluna SLA
            for c in df_cur.columns:
                if 'SLA' in str(c):
                    df_cur.rename(columns={c: 'SLA (%)'}, inplace=True)
                    df_cur['SLA (%)'] = pd.to_numeric(df_cur['SLA (%)'], errors='coerce')
                    break

        # Prepara anterior
        df_prev = None
        if df_prev_month is not None and not df_prev_month.empty:
            df_prev = df_prev_month[['Host', 'SLA_anterior']].copy()
            df_prev['SLA_anterior'] = pd.to_numeric(df_prev['SLA_anterior'], errors='coerce')

        # Junta delta por Host
        df = df_cur[['Host', 'SLA (%)']].copy()
        if df_prev is not None:
            df = df.merge(df_prev, on='Host', how='left')
            df['Delta'] = df['SLA (%)'] - df['SLA_anterior']
        else:
            df['SLA_anterior'] = None
            df['Delta'] = None

        # KPIs
        cards_html = ''
        if show_cards:
            avg_cur = float(df['SLA (%)'].mean()) if not df.empty else 0.0
            avg_prev = float(df['SLA_anterior'].mean()) if df_prev is not None else None
            delta_avg = (avg_cur - avg_prev) if avg_prev is not None else None
            below_count = 0
            if target_sla is not None:
                below_count = df[df['SLA (%)'] < float(target_sla)].shape[0]
            cards_html = self.render_partial('modules/_cards_sla_plus.html', {
                'avg_cur': avg_cur, 'avg_prev': avg_prev, 'delta_avg': delta_avg, 'below_count': below_count,
                'target_sla': target_sla
            })

        # Abaixo da meta
        below_html = ''
        below_csv = ''
        if show_below and target_sla is not None:
            df_below = df[df['SLA (%)'] < float(target_sla)].copy()
            df_below['Gap Meta'] = float(target_sla) - df_below['SLA (%)']
            df_below = df_below.sort_values(by='SLA (%)').head(top_n)
            below_html = self._simple_table(df_below[['Host', 'SLA (%)', 'Gap Meta', 'Delta']])
            try:
                import base64
                csv = df_below[['Host', 'SLA (%)', 'Gap Meta', 'Delta']].to_csv(index=False, sep=';')
                below_csv = base64.b64encode(csv.encode('utf-8')).decode('ascii')
            except Exception:
                below_csv = ''

        # Top regressões e melhoras
        reg_html = ''
        imp_html = ''
        reg_csv = ''
        imp_csv = ''
        if df_prev is not None:
            try:
                df_valid = df.dropna(subset=['Delta']).copy()
                if min_delta > 0:
                    df_reg = df_valid[df_valid['Delta'] <= -abs(min_delta)]
                    df_imp = df_valid[df_valid['Delta'] >= abs(min_delta)]
                else:
                    df_reg, df_imp = df_valid, df_valid
                if show_reg:
                    reg = df_reg.sort_values(by='Delta').head(top_n)
                    reg_html = self._simple_table(reg[['Host', 'SLA_anterior', 'SLA (%)', 'Delta']])
                    try:
                        import base64
                        reg_csv = base64.b64encode(reg[['Host', 'SLA_anterior', 'SLA (%)', 'Delta']].to_csv(index=False, sep=';').encode('utf-8')).decode('ascii')
                    except Exception:
                        reg_csv = ''
                if show_imp:
                    imp = df_imp.sort_values(by='Delta', ascending=False).head(top_n)
                    imp_html = self._simple_table(imp[['Host', 'SLA_anterior', 'SLA (%)', 'Delta']])
                    try:
                        import base64
                        imp_csv = base64.b64encode(imp[['Host', 'SLA_anterior', 'SLA (%)', 'Delta']].to_csv(index=False, sep=';').encode('utf-8')).decode('ascii')
                    except Exception:
                        imp_csv = ''
            except Exception:
                pass

        return self.render('sla_plus', {
            'cards': cards_html,
            'below_table': below_html,
            'reg_table': reg_html,
            'imp_table': imp_html,
            'below_csv': below_csv,
            'reg_csv': reg_csv,
            'imp_csv': imp_csv
        })

    def _simple_table(self, df):
        if df is None or df.empty:
            return '<p><i>Sem dados.</i></p>'
        df2 = df.copy()
        for c in df2.columns:
            if df2[c].dtype == float:
                df2[c] = df2[c].map(lambda v: f"{v:.2f}".replace('.', ',') if pd.notna(v) else '')
        return df2.to_html(classes='table', index=False, escape=False)
