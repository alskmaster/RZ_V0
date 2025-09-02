import pandas as pd
from .base_collector import BaseCollector
from app.charting import generate_chart


class SlaChartCollector(BaseCollector):
    """
    Renderiza um gráfico horizontal (barh) de SLA por Host.
    Reaproveita availability_data do ReportGenerator.
    """

    def collect(self, all_hosts, period, availability_data, df_prev_month=None):
        self._update_status("Montando Gráfico de SLA...")

        df_sla = availability_data.get('df_sla_problems', pd.DataFrame()).copy()
        if df_sla.empty:
            return self.render('sla_chart', {'chart': None, 'note': '<p><i>Nenhum dado de disponibilidade.</i></p>'})

        opts = self.module_config.get('custom_options', {}) or {}
        top_n = int(opts.get('top_n', 0) or 0)
        order = str(opts.get('order', 'asc')).lower()  # asc/desc
        color = opts.get('color', '#2c7be5')
        # Nova opções (engrenagem): meta de SLA, destaque abaixo da meta, e limitar eixo X em 0..100
        target_sla = None
        try:
            target_sla = float(opts.get('target_sla')) if opts.get('target_sla') is not None else None
        except Exception:
            target_sla = None
        if target_sla is None:
            try:
                target_sla = float(self.generator._get_client_sla_contract() or 0)
            except Exception:
                target_sla = None
        below_color = opts.get('below_color', '#e55353')
        force_percent_axis = bool(opts.get('x_axis_0_100', True))

        # Keep only needed columns
        if 'SLA (%)' not in df_sla.columns:
            # Em cenários com colunas renomeadas, tenta achar alguma
            candidates = [c for c in df_sla.columns if 'SLA' in str(c)]
            if not candidates:
                return self.render('sla_chart', {'chart': None, 'note': '<p><i>Coluna de SLA não encontrada.</i></p>'})
            sla_col = candidates[0]
        else:
            sla_col = 'SLA (%)'

        df_plot = df_sla[['Host', sla_col]].dropna()
        try:
            df_plot[sla_col] = pd.to_numeric(df_plot[sla_col], errors='coerce')
        except Exception:
            pass
        df_plot = df_plot.dropna()

        ascending = True if order == 'asc' else False
        df_plot = df_plot.sort_values(by=sla_col, ascending=ascending)
        if top_n > 0:
            df_plot = df_plot.head(top_n) if ascending else df_plot.tail(top_n)

        chart = generate_chart(
            df_plot,
            x_col=sla_col,
            y_col='Host',
            title=self.module_config.get('title') or 'Disponibilidade por Host (%)',
            x_label='SLA (%)',
            chart_color=color,
            target_line=target_sla,
            below_color=below_color,
            above_color=color,
            xlim=(0, 100) if force_percent_axis else None,
        )
        return self.render('sla_chart', {'chart': chart, 'note': ''})
