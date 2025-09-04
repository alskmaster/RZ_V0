from .base_collector import BaseCollector
from flask import current_app
import datetime as dt
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64


class UnavailabilityHeatmapCollector(BaseCollector):
    """
    Mapa de Calor de Indisponibilidade

    - Objetivo: visualizar frequência de incidentes (PROBLEM) por dia da semana (linhas) e hora (colunas).
    - Respeita Cliente e Mês do gerar_form (via all_hosts e period). Opcionalmente aplica sub-filtro de período.

    custom_options suportadas:
      - severities: [info, warning, average, high, disaster] (default: todas)
      - host_name_contains: filtro textual por host visível
      - period_sub_filter: full_month | last_24h | last_7d (default: full_month)
      - palette: nome de colormap do matplotlib (default: 'OrRd')
      - annotate: bool, insere números no heatmap (default: True)
    """

    _SEVERITY_FILTER_MAP = {
        'info': '1', 'warning': '2', 'average': '3', 'high': '4', 'disaster': '5', 'not_classified': '0'
    }

    _DAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

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

    def _img(self, matrix, palette='OrRd', annotate=True):
        fig, ax = plt.subplots(figsize=(12, 4.8))
        mat = np.array(matrix, dtype=float)
        im = ax.imshow(mat, aspect='auto', cmap=palette, origin='upper')
        ax.set_yticks(range(7))
        ax.set_yticklabels(self._DAYS)
        ax.set_xticks(range(24))
        ax.set_xticklabels([f"{h:02d}h" for h in range(24)], rotation=45, ha='right')
        ax.set_xlabel('Hora do dia')
        ax.set_ylabel('Dia da semana')
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Incidentes (contagem)')
        if annotate:
            for i in range(7):
                for j in range(24):
                    v = mat[i, j]
                    if v > 0:
                        ax.text(j, i, int(v), ha='center', va='center', color='black', fontsize=8)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def collect(self, all_hosts, period):
        o = self.module_config.get('custom_options', {}) or {}
        severities = o.get('severities', ['info', 'warning', 'average', 'high', 'disaster'])
        ids = [self._SEVERITY_FILTER_MAP[s] for s in severities if s in self._SEVERITY_FILTER_MAP]
        host_contains = (o.get('host_name_contains') or '').strip()
        palette = o.get('palette', 'OrRd')
        annotate = o.get('annotate', True)
        period = self._apply_period_subfilter(period, o.get('period_sub_filter', 'full_month'))

        if host_contains:
            try:
                all_hosts = [h for h in (all_hosts or []) if host_contains.lower() in str(h.get('nome_visivel','')).lower()]
            except Exception:
                pass
        if not all_hosts:
            return self.render('unavailability_heatmap', {
                'error': 'Nenhum host disponível para o período/filtro informado.',
                'chart_b64': None,
            })

        all_host_ids = [h['hostid'] for h in all_hosts]
        problems = self.generator.obter_eventos_wrapper(all_host_ids, period, 'hostids')
        if problems is None:
            # Fallback robusto: quebra em dias para reduzir carga no Zabbix
            try:
                self._update_status('Consulta pesada detectada. Coletando eventos por dia...')
                start_ts, end_ts = int(period['start']), int(period['end'])
                day_seconds = 24 * 3600
                parts = []
                cur = start_ts
                while cur <= end_ts:
                    end_part = min(end_ts, cur + day_seconds - 1)
                    p = {'start': cur, 'end': end_part}
                    evs = self.generator.obter_eventos(all_host_ids, p, 'hostids', max_depth=1)
                    if isinstance(evs, list) and evs:
                        parts.extend(evs)
                    cur = end_part + 1
                problems = parts
            except Exception:
                problems = None
        if problems is None:
            self._update_status('Erro ao coletar eventos para heatmap.')
            return self.render('unavailability_heatmap', {'error': 'Falha ao coletar eventos.'})

        df = pd.DataFrame(problems)
        if df.empty:
            return self.render('unavailability_heatmap', {'chart_b64': None})

        for c in ('source', 'object', 'value', 'severity', 'clock'):
            if c in df.columns:
                df[c] = df[c].astype(str)
        df = df[(df['source'] == '0') & (df['object'] == '0') & (df['value'] == '1')]
        if ids:
            df = df[df['severity'].astype(str).isin(ids)]
        if df.empty:
            return self.render('unavailability_heatmap', {'chart_b64': None})

        try:
            df['clock_ts'] = pd.to_numeric(df['clock'], errors='coerce').fillna(0).astype(int)
        except Exception:
            df['clock_ts'] = 0
        df['dt'] = pd.to_datetime(df['clock_ts'], unit='s')
        df['dow'] = (df['dt'].dt.dayofweek).astype(int)  # 0=Mon ... 6=Sun
        df['hour'] = df['dt'].dt.hour.astype(int)

        mat = [[0 for _ in range(24)] for __ in range(7)]
        for _, r in df.iterrows():
            dow = int(r.get('dow', 0))
            hour = int(r.get('hour', 0))
            if 0 <= dow <= 6 and 0 <= hour <= 23:
                mat[dow][hour] += 1

        chart_b64 = self._img(mat, palette=palette, annotate=bool(annotate))
        total = int(np.sum(mat))
        summary = f"Mapa de calor baseado em {total} incidente(s) no período selecionado."

        return self.render('unavailability_heatmap', {
            'chart_b64': chart_b64,
            'summary_text': summary,
        })
