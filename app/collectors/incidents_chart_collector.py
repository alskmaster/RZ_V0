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
    Módulo Incidentes (Gráficos): apenas visualizaçõeses (sem tabelas).
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
        fig.savefig(buf, format='png', bbox_inches='tight')
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

    def _daily(self, df, chart_type='bar', rotate=False, alternate=False, granularity='D'):
        if df.empty:
            return None
        df['clock_dt'] = pd.to_datetime(df['clock'], unit='s')
        rule = granularity or 'D'
        s = df.set_index('clock_dt').resample(rule).size()
        if s.empty:
            return None
        fig, ax = plt.subplots(figsize=(12, 6))
        if chart_type == 'bar':
            ax.bar(s.index, s.values, color='#e57373', edgecolor='white', linewidth=0.7)
        else:
            ax.plot(s.index, s.values, marker='o', linestyle='-', color='#1e88e5')
        ax.set_title('Volume Diario de Incidentes')
        ax.set_xlabel('Data')
        ax.set_ylabel('Incidentes')
        ax.grid(True, linestyle='--', alpha=0.7)
        # Formatador e locator por granularidade
        if rule == 'M':
            ax.xaxis.set_major_locator(plt.matplotlib.dates.MonthLocator(interval=1))
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%m/%y'))
        elif rule == 'W':
            ax.xaxis.set_major_locator(plt.matplotlib.dates.WeekdayLocator())
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m'))
        else:
            ax.xaxis.set_major_locator(plt.matplotlib.dates.DayLocator(interval=1))
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d/%m'))
        if rotate:
            plt.xticks(rotation=45, ha='right')
        if rule == 'D' and alternate and len(ax.get_xticklabels()) > 1:
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
        if chart_type == 'line':
            for sev in cols:
                color = self._SEVERITY_COLORS.get(sev, '#607d8b')
                ax.plot(pivot.index, pivot[sev].values, marker='o', linestyle='-', label=sev, color=color)
        else:
            bottom = np.zeros(len(pivot))
            for sev in cols:
                values = pivot[sev].values
                color = self._SEVERITY_COLORS.get(sev, '#607d8b')
                ax.bar(pivot.index, values, bottom=bottom, label=sev, color=color, edgecolor='white', linewidth=0.7)
                bottom += values
        ax.set_title('Volume Diario por Severidade')
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
        try:
            _tn = int(o.get('problem_type_top_n')) if o.get('problem_type_top_n') is not None else 10
        except Exception:
            _tn = 10
        top_n = None if (_tn is not None and _tn <= 0) else _tn
        daily_type = o.get('daily_volume_chart_type', 'bar')
        # Unificação: usar as mesmas severidades globais quando não houver seleção especí­fica
        daily_sev = o.get('daily_volume_severities') or severities
        rotate = o.get('x_axis_rotate_labels', True)
        alternate = o.get('x_axis_alternate_days', True)
        ack_filter = (o.get('ack_filter') or 'all').lower()

        # Pró-filtros por host (texto)
        host_contains = (o.get('host_name_contains') or '').strip().lower()
        excl_hosts = [s.strip().lower() for s in (o.get('exclude_hosts_contains') or '').split(',') if s.strip()]
        if host_contains:
            try:
                all_hosts = [h for h in (all_hosts or []) if host_contains in str(h.get('nome_visivel','')).lower()]
            except Exception:
                pass
        if excl_hosts:
            try:
                def _hex(h):
                    nm = str(h.get('nome_visivel','')).lower()
                    return any(t in nm for t in excl_hosts)
                all_hosts = [h for h in (all_hosts or []) if not _hex(h)]
            except Exception:
                pass
        all_host_ids = [h['hostid'] for h in (all_hosts or [])]
        problems = self.generator.obter_eventos_wrapper(all_host_ids, period, 'hostids')
        if problems is None:
            self._update_status("Erro ao coletar eventos de incidentes (gráficos).")
            return self.render('incidents_chart', {"error": "Não foi possível coletar dados de incidentes."})

        df = pd.DataFrame(problems)
        if df.empty:
            return self.render('incidents_chart', {'total_incidents': 0, 'severity_counts': {}, 'charts': {}})

        # Normalização e filtros
        for c in ('value', 'severity', 'source', 'object'):
            if c in df.columns:
                df[c] = df[c].astype(str)
        # Garante colunas essenciais para filtragem e agregações
        for required in ('clock', 'name', 'objectid'):
            if required not in df.columns:
                df[required] = None
        mask = pd.Series([True]*len(df))
        if 'source' in df.columns:
            mask &= (df['source'] == '0')
        if 'object' in df.columns:
            mask &= (df['object'] == '0')
        if 'value' in df.columns:
            mask &= (df['value'] == '1')
        df = df[mask]
        if ids:
            df = df[df['severity'].astype(str).isin(ids)]
        # Filtro por ACK (se solicitado)
        if 'acknowledged' in df.columns and ack_filter in ('only_acked', 'only_unacked'):
            flag = '1' if ack_filter == 'only_acked' else '0'
            try:
                df = df[df['acknowledged'].astype(str) == flag]
            except Exception:
                pass
        # Filtros por trigger name
        trig_contains = (o.get('trigger_name_contains') or '').strip().lower()
        excl_trigs = [s.strip().lower() for s in (o.get('exclude_triggers_contains') or '').split(',') if s.strip()]
        if trig_contains:
            try:
                df = df[df['name'].astype(str).str.lower().str.contains(trig_contains, na=False)]
            except Exception:
                pass
        if excl_trigs:
            try:
                df = df[~df['name'].astype(str).str.lower().apply(lambda nm: any(t in nm for t in excl_trigs))]
            except Exception:
                pass
        if df.empty:
            return self.render('incidents_chart', {'total_incidents': 0, 'severity_counts': {}, 'charts': {}})
        # Filtros por tags (se presentes nos eventos)
        tags_inc = [t.strip().lower() for t in (o.get('tags_include') or '').split(',') if t.strip()]
        tags_exc = [t.strip().lower() for t in (o.get('tags_exclude') or '').split(',') if t.strip()]
        if ('tags' in df.columns) and (tags_inc or tags_exc):
            def _norm_tags(tlist):
                try:
                    return [ (str((tt.get('tag') if isinstance(tt, dict) else '')) + ':' + str((tt.get('value') if isinstance(tt, dict) else ''))).lower() for tt in (tlist or []) if isinstance(tt, dict) ]
                except Exception:
                    return []
            try:
                df['_tag_strs'] = df['tags'].apply(_norm_tags)
                if tags_inc:
                    df = df[df['_tag_strs'].apply(lambda lst: any(any(inc in s for s in lst) for inc in tags_inc))]
                if tags_exc:
                    df = df[~df['_tag_strs'].apply(lambda lst: any(any(exc in s for s in lst) for exc in tags_exc))]
            except Exception:
                pass

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
            # Top problemas por chave (name ou triggerid)
            problem_key = (o.get('problem_type_key') or 'triggerid').lower()
            try:
                if problem_key == 'triggerid':
                    df['tid'] = df['objectid'].astype(str)
                    counts = df['tid'].value_counts()
                    if top_n is not None:
                        counts = counts.head(top_n)
                    name_mode = (df.groupby(['tid','name']).size().reset_index(name='n')
                                   .sort_values(['tid','n'], ascending=[True, False])
                                   .drop_duplicates('tid')
                                   .set_index('tid')['name'])
                    labels = [name_mode.get(tid, f'Trigger {tid}') for tid in counts.index]
                    charts['problem_type_bar'] = self._bar(labels, list(counts.values), 'Top Incidentes por Tipo de Problema', 'Problema', 'Incidentes', rotate=True)
                else:
                    # Agrupa por 'name'
                    df['__name'] = df['name'].astype(str).fillna('N/A')
                    pc = df['__name'].value_counts()
                    if top_n is not None:
                        pc = pc.head(top_n)
                    charts['problem_type_bar'] = self._bar(list(pc.index), list(pc.values), 'Top Incidentes por Tipo de Problema', 'Problema', 'Incidentes', rotate=True)
            except Exception:
                # Se algo der errado, não quebra o módulo; apenas não desenha o gráfico
                pass
        elif chart_type in ('daily_volume', 'daily_volume_severity'):
            ddf = df
            if chart_type == 'daily_volume_severity' and daily_sev:
                daily_ids = [self._SEVERITY_FILTER_MAP[s] for s in daily_sev if s in self._SEVERITY_FILTER_MAP]
                ddf = ddf[ddf['severity'].astype(str).isin(daily_ids)]
            if chart_type == 'daily_volume_severity':
                charts['daily_volume'] = self._daily_by_severity(ddf, chart_type=daily_type, rotate=rotate, alternate=alternate)
            else:
                granularity = (o.get('time_granularity') or 'D').upper()
                if granularity not in ('D','W','M'):
                    granularity = 'D'
                charts['daily_volume'] = self._daily(ddf, chart_type=daily_type, rotate=rotate, alternate=alternate, granularity=granularity)

        return self.render('incidents_chart', {
            'total_incidents': total,
            'severity_counts': severity_counts,
            'charts': charts,
            'chart_type': chart_type,
            'daily_volume_severities': daily_sev if chart_type == 'daily_volume_severity' else [],
        })

