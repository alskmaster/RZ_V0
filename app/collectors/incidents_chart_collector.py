from .base_collector import BaseCollector
import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64


class IncidentsChartCollector(BaseCollector):
    """
    Módulo Incidentes (Gráficos): apenas visualizações (sem tabelas).
    Opções suportadas (custom_options):
      - severities: [info, warning, average, high, disaster]
      - period_sub_filter: full_month | last_24h | last_7d
      - chart_type: severity_pie | severity_bar | problem_type_bar | daily_volume | daily_volume_severity
      - problem_type_top_n: int
      - daily_volume_chart_type: bar | line
      - daily_volume_severities: [...]
      - x_axis_rotate_labels: bool
      - x_axis_alternate_days: bool
    """

    _SEVERITY_MAP = {
        '0': 'Não Classificado',
        '1': 'Informação',
        '2': 'Atenção',
        '3': 'Média',
        '4': 'Alta',
        '5': 'Desastre'
    }
    _SEVERITY_ORDER = ['Não Classificado', 'Informação', 'Atenção', 'Média', 'Alta', 'Desastre']
    _SEVERITY_COLORS = {
        'Não Classificado': '#9e9e9e',
        'Informação': '#2196f3',
        'Atenção': '#ffb300',
        'Média': '#fb8c00',
        'Alta': '#e53935',
        'Desastre': '#8e0000',
    }
    _SEVERITY_FILTER_MAP = {
        'info': '1',
        'warning': '2',
        'average': '3',
        'high': '4',
        'disaster': '5',
        'not_classified': '0',
    }

    def _apply_period_subfilter(self, period, sub):
        start, end = period['start'], period['end']
        if sub == 'last_24h':
            end = int(datetime.datetime.now().timestamp())
            start = end - 24 * 3600
        elif sub == 'last_7d':
            end = int(datetime.datetime.now().timestamp())
            start = end - 7 * 24 * 3600
        return {'start': start, 'end': end}

    def _img(self, fig):
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def _pie(self, counts):
        if not counts:
            return None
        # Ordena por ordem de severidade conhecida
        labels = [s for s in self._SEVERITY_ORDER if s in counts]
        sizes = [counts[s] for s in labels]
        colors = [self._SEVERITY_COLORS.get(s, '#607d8b') for s in labels]
        fig, ax = plt.subplots(figsize=(7, 7))
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, textprops={'fontsize': 9})
        ax.axis('equal')
        return self._img(fig)

    def _bar(self, labels, values, title, xlabel, ylabel, rotate=False, colors=None):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(labels, values, color=colors or '#2962ff', edgecolor='white', linewidth=0.7)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if rotate:
            plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        return self._img(fig)

    def _daily(self, df, chart_type='bar', rotate=False, alternate=False):
        if df.empty:
            return None
        df['clock_dt'] = pd.to_datetime(df['clock'], unit='s')
        s = df.set_index('clock_dt').resample('D').size()
        if s.empty:
            return None
        fig, ax = plt.subplots(figsize=(12, 6))
        if chart_type == 'bar':
            ax.bar(s.index, s.values, color='#e57373', edgecolor='white', linewidth=0.7)
        else:
            ax.plot(s.index, s.values, marker='o', linestyle='-', color='#1e88e5')
        ax.set_title('Volume Diário de Incidentes')
        ax.set_xlabel('Data')
        ax.set_ylabel('Incidentes')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m'))
        if rotate:
            plt.xticks(rotation=45, ha='right')
        if alternate and len(ax.get_xticklabels()) > 1:
            loc = plt.matplotlib.dates.DayLocator(interval=1)
            ax.xaxis.set_major_locator(loc)
            for i, lab in enumerate(ax.get_xticklabels()):
                if i % 2:
                    lab.set_visible(False)
        plt.tight_layout()
        return self._img(fig)

    def _daily_by_severity(self, df, chart_type='bar', rotate=False, alternate=False):
        """Stacked bars por severidade ao longo dos dias."""
        if df.empty:
            return None
        df['clock_dt'] = pd.to_datetime(df['clock'], unit='s')
        df['date'] = df['clock_dt'].dt.floor('D')
        pivot = (
            df.groupby(['date', 'severity_name'])
              .size()
              .unstack(fill_value=0)
        )
        # Ordena as colunas conforme severidade
        cols = [s for s in self._SEVERITY_ORDER if s in pivot.columns]
        pivot = pivot[cols]
        if pivot.empty:
            return None
        fig, ax = plt.subplots(figsize=(12, 6))
        bottom = np.zeros(len(pivot))
        for sev in cols:
            values = pivot[sev].values
            color = self._SEVERITY_COLORS.get(sev, '#607d8b')
            ax.bar(pivot.index, values, bottom=bottom, label=sev, color=color, edgecolor='white', linewidth=0.7)
            bottom += values
        ax.set_title('Volume Diário por Severidade')
        ax.set_xlabel('Data')
        ax.set_ylabel('Incidentes')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m'))
        if rotate:
            plt.xticks(rotation=45, ha='right')
        if alternate and len(ax.get_xticklabels()) > 1:
            loc = plt.matplotlib.dates.DayLocator(interval=1)
            ax.xaxis.set_major_locator(loc)
            for i, lab in enumerate(ax.get_xticklabels()):
                if i % 2:
                    lab.set_visible(False)
        ax.legend(ncol=min(3, len(cols)), fontsize=9, frameon=False)
        plt.tight_layout()
        return self._img(fig)

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {})
        severities = o.get('severities', ['info', 'warning', 'average', 'high', 'disaster'])
        ids = [self._SEVERITY_FILTER_MAP[s] for s in severities if s in self._SEVERITY_FILTER_MAP]
        period = self._apply_period_subfilter(period, o.get('period_sub_filter', 'full_month'))
        chart_type = o.get('chart_type', 'severity_pie')
        top_n = int(o.get('problem_type_top_n') or 10)
        daily_type = o.get('daily_volume_chart_type', 'bar')
        daily_sev = o.get('daily_volume_severities') or []
        rotate = o.get('x_axis_rotate_labels', True)
        alternate = o.get('x_axis_alternate_days', True)

        all_host_ids = [h['hostid'] for h in all_hosts]
        problems = self.generator.obter_eventos_wrapper(all_host_ids, period, 'hostids')
        if problems is None:
            self._update_status("Erro ao coletar eventos de incidentes (gráficos).")
            return self.render('incidents_chart', {"error": "Não foi possível coletar dados de incidentes."})

        df = pd.DataFrame(problems)
        if df.empty:
            return self.render('incidents_chart', {'total_incidents': 0, 'severity_counts': {}, 'charts': {}})

        # Normalização e filtros
        for c in ('source', 'object', 'value', 'severity'):
            if c in df.columns:
                df[c] = df[c].astype(str)
        df = df[(df['source'] == '0') & (df['object'] == '0') & (df['value'] == '1')]
        if ids:
            df = df[df['severity'].astype(str).isin(ids)]
        if df.empty:
            return self.render('incidents_chart', {'total_incidents': 0, 'severity_counts': {}, 'charts': {}})

        # Mapeia nomes de severidade
        df['severity_name'] = df['severity'].astype(str).map(self._SEVERITY_MAP).fillna('Desconhecido')
        total = len(df)

        charts = {}
        severity_counts = df['severity_name'].value_counts().to_dict()
        if chart_type == 'severity_pie':
            charts['severity_pie'] = self._pie(severity_counts)
        elif chart_type == 'severity_bar':
            labels_order = [s for s in self._SEVERITY_ORDER if s in severity_counts]
            values = [severity_counts[s] for s in labels_order]
            colors = [self._SEVERITY_COLORS.get(s, '#607d8b') for s in labels_order]
            charts['severity_bar'] = self._bar(labels_order, values, 'Incidentes por Severidade', 'Severidade', 'Incidentes', rotate=False, colors=colors)
        elif chart_type == 'problem_type_bar':
            # Top N problemas por nome
            pc = df['name'].value_counts().head(top_n)
            charts['problem_type_bar'] = self._bar(list(pc.index), list(pc.values), 'Top Incidentes por Tipo de Problema', 'Problema', 'Incidentes', rotate=True)
        elif chart_type in ('daily_volume', 'daily_volume_severity'):
            ddf = df
            if chart_type == 'daily_volume_severity' and daily_sev:
                daily_ids = [self._SEVERITY_FILTER_MAP[s] for s in daily_sev if s in self._SEVERITY_FILTER_MAP]
                ddf = ddf[ddf['severity'].astype(str).isin(daily_ids)]
            if chart_type == 'daily_volume_severity':
                charts['daily_volume'] = self._daily_by_severity(ddf, chart_type=daily_type, rotate=rotate, alternate=alternate)
            else:
                charts['daily_volume'] = self._daily(ddf, chart_type=daily_type, rotate=rotate, alternate=alternate)

        return self.render('incidents_chart', {
            'total_incidents': total,
            'severity_counts': severity_counts,
            'charts': charts,
            'chart_type': chart_type,
            'daily_volume_severities': daily_sev if chart_type == 'daily_volume_severity' else [],
        })
