# app/collectors/traffic_out_chart_collector.py
import base64
import datetime as dt
from io import BytesIO
import textwrap

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart, generate_multi_line_chart


class TrafficOutChartCollector(BaseCollector):
    """Modulo Trafego de Saida (Graficos) com filtros e opcoes visuais."""

    DEFAULT_TITLE = 'Trafego de Saida (Graficos)'

    def _normalize_interfaces(self, interfaces):
        return [str(item).strip() for item in (interfaces or []) if str(item).strip()]

    def _get_chunk_size(self):
        try:
            return int(self.module_config.get('trend_chunk_size') or 150)
        except Exception:
            return 150

    def _apply_period_subfilter(self, period, sub_filter):
        sub = (sub_filter or 'full_month').lower()
        try:
            start = int(period.get('start'))
            end = int(period.get('end'))
        except Exception:
            start = int(dt.datetime.now().timestamp()) - 30 * 24 * 3600
            end = int(dt.datetime.now().timestamp())
        now = int(dt.datetime.now().timestamp())
        if sub == 'last_24h':
            end = now
            start = end - 24 * 3600
        elif sub == 'last_7d':
            end = now
            start = end - 7 * 24 * 3600
        return {'start': int(start), 'end': int(end)}

    def _get_dataset(self, all_hosts, period, interfaces):
        interfaces_list = self._normalize_interfaces(interfaces)
        chunk_size = self._get_chunk_size()
        key_interfaces = ','.join(sorted(interfaces_list)) if interfaces_list else 'all'
        cache_key = f"traffic_out::{key_interfaces}::{int(period.get('start', 0))}::{int(period.get('end', 0))}::{chunk_size}"
        cache_bucket = self.generator.cached_data.setdefault('traffic_out_shared', {})
        if cache_key not in cache_bucket:
            df_base, message = self.generator.shared_collect_traffic(
                all_hosts,
                period,
                'net.if.out',
                interfaces=interfaces_list,
                chunk_size=chunk_size,
            )
            if not isinstance(df_base, pd.DataFrame):
                df_base = pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max'])
            cache_bucket[cache_key] = {'df': df_base, 'message': message}
        cached = cache_bucket[cache_key]
        df_copy = cached['df'].copy() if isinstance(cached.get('df'), pd.DataFrame) else pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max'])
        return df_copy, cached.get('message'), interfaces_list

    def _pie(self, df, label_wrap=48, show_values=True):
        fig = None
        try:
            if 'Avg' not in df.columns:
                return None
            labels = df['Host'].astype(str).tolist()
            width = int(label_wrap) if label_wrap else 48
            wrapped = ['\n'.join(textwrap.wrap(label, width=width)) if label else '' for label in labels]
            sizes = pd.to_numeric(df['Avg'], errors='coerce').fillna(0).tolist()
            if not any(sizes):
                return None
            plt.style.use('seaborn-v0_8-whitegrid')
            fig, ax = plt.subplots(figsize=(9, 6))
            autopct = '%1.1f%%' if show_values else None
            ax.pie(sizes, labels=wrapped, autopct=autopct, startangle=90, textprops={'fontsize': 9})
            ax.axis('equal')
            plt.tight_layout()
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, transparent=True)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception:
            return None
        finally:
            if fig is not None:
                plt.close(fig)

    def _build_summary(self, period, chart_type, item_count, top_n, interfaces):
        try:
            start_txt = dt.datetime.fromtimestamp(int(period['start'])).strftime('%d/%m/%Y')
            end_txt = dt.datetime.fromtimestamp(int(period['end'])).strftime('%d/%m/%Y')
            period_txt = f"{start_txt} a {end_txt}"
        except Exception:
            period_txt = 'periodo selecionado'
        chart_names = {'pie': 'Pizza', 'line': 'Linha', 'bar': 'Barras'}
        summary = (
            f"Grafico de Trafego de Saida por host ({chart_names.get(chart_type, 'Barras')}). "
            "Estatisticas de Minimo, Medio e Maximo em Mbps. "
            f"Periodo: {period_txt}. Itens exibidos: {item_count}."
        )
        if top_n and top_n > 0:
            summary += f" Top N aplicado: {top_n}."
        if interfaces:
            summary += f" Interfaces filtradas: {', '.join(interfaces)}."
        return summary

    def collect(self, all_hosts, period):
        options = self.module_config.get('custom_options', {}) or {}
        period_filtered = self._apply_period_subfilter(period, options.get('period_sub_filter', 'full_month'))
        interfaces = self.module_config.get('interfaces', [])
        df, base_message, interfaces_list = self._get_dataset(all_hosts, period_filtered, interfaces)

        host_contains = (options.get('host_name_contains') or '').strip()
        exclude_raw = (options.get('exclude_hosts_contains') or '')
        exclude_terms = [term.strip().lower() for term in exclude_raw.split(',') if term.strip()]
        raw_top = options.get('top_n')
        try:
            top_n = int(raw_top)
        except Exception:
            top_n = 5
        if top_n < 0:
            top_n = 0
        chart_type = (options.get('chart_type') or 'bar').lower()
        rotate_x = bool(options.get('rotate_x_labels'))
        show_values = bool(options.get('show_values', False))
        try:
            label_wrap = int(options.get('label_wrap') or 48)
        except Exception:
            label_wrap = 48
        show_summary = bool(options.get('show_summary', True))
        colors = [
            options.get('color_max') or '#85e085',
            options.get('color_avg') or '#33cc33',
            options.get('color_min') or '#248f24',
        ]

        df_filtered = df.copy()
        if not df_filtered.empty and host_contains:
            try:
                df_filtered = df_filtered[df_filtered['Host'].astype(str).str.contains(host_contains, case=False, na=False)]
            except Exception:
                pass
        if not df_filtered.empty and exclude_terms:
            try:
                mask = ~df_filtered['Host'].astype(str).str.lower().apply(lambda value: any(term in value for term in exclude_terms))
                df_filtered = df_filtered[mask]
            except Exception:
                pass
        if not df_filtered.empty:
            for column in ['Min', 'Avg', 'Max']:
                if column in df_filtered.columns:
                    df_filtered[column] = pd.to_numeric(df_filtered[column], errors='coerce')
            if top_n and top_n > 0:
                try:
                    df_filtered = df_filtered.sort_values(by='Avg', ascending=False).head(top_n)
                except Exception:
                    df_filtered = df_filtered.head(top_n)

        warning_text = base_message
        image = None
        normalized_chart_type = chart_type if chart_type in {'pie', 'line', 'bar'} else 'bar'
        if df_filtered.empty:
            if not warning_text:
                warning_text = 'Sem dados de trafego para os filtros informados.'
        else:
            title = 'Trafego de Saida (Mbps)'
            if normalized_chart_type == 'pie':
                image = self._pie(df_filtered, label_wrap=label_wrap, show_values=show_values)
                if image is None:
                    warning_text = warning_text or 'Nao foi possivel gerar grafico de pizza com os dados informados.'
            elif normalized_chart_type == 'line':
                image = generate_multi_line_chart(
                    df_filtered,
                    title,
                    'Mbps',
                    colors,
                    label_wrap=label_wrap,
                    show_values=show_values,
                    rotate_x=rotate_x,
                )
                if image is None:
                    warning_text = warning_text or 'Nao foi possivel gerar grafico de linha com os dados informados.'
            else:
                normalized_chart_type = 'bar'
                image = generate_multi_bar_chart(
                    df_filtered,
                    title,
                    'Mbps',
                    colors,
                    label_wrap=label_wrap,
                    show_values=show_values,
                    rotate_x=rotate_x,
                )
                if image is None:
                    warning_text = warning_text or 'Nao foi possivel gerar grafico de barras com os dados informados.'

        summary_text = None
        if show_summary:
            summary_text = self._build_summary(
                period_filtered,
                normalized_chart_type,
                len(df_filtered),
                top_n if top_n and top_n > 0 else None,
                interfaces_list,
            )

        if not self.module_config.get('title'):
            self.module_config['title'] = self.DEFAULT_TITLE

        return self.render('traffic_out_chart', {
            'img': image,
            'summary_text': summary_text,
            'warning_text': warning_text,
        })
