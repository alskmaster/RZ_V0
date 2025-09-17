# app/collectors/traffic_in_table_collector.py
import datetime as dt

import pandas as pd

from .base_collector import BaseCollector


class TrafficInTableCollector(BaseCollector):
    """Modulo Trafego de Entrada (Tabela) com filtros, ordenacao e resumo."""

    DEFAULT_TITLE = 'Trafego de Entrada (Tabela)'

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
        cache_key = f"traffic_in::{key_interfaces}::{int(period.get('start', 0))}::{int(period.get('end', 0))}::{chunk_size}"
        cache_bucket = self.generator.cached_data.setdefault('traffic_in_shared', {})
        if cache_key not in cache_bucket:
            df_base, message = self.generator.shared_collect_traffic(
                all_hosts,
                period,
                'net.if.in',
                interfaces=interfaces_list,
                chunk_size=chunk_size,
            )
            if not isinstance(df_base, pd.DataFrame):
                df_base = pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max'])
            cache_bucket[cache_key] = {'df': df_base, 'message': message}
        cached = cache_bucket[cache_key]
        df_copy = cached['df'].copy() if isinstance(cached.get('df'), pd.DataFrame) else pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max'])
        return df_copy, cached.get('message'), interfaces_list

    def _format_summary(self, period, sort_by, sort_asc, total_rows, top_n, interfaces):
        try:
            start_txt = dt.datetime.fromtimestamp(int(period['start'])).strftime('%d/%m/%Y')
            end_txt = dt.datetime.fromtimestamp(int(period['end'])).strftime('%d/%m/%Y')
            period_txt = f"{start_txt} a {end_txt}"
        except Exception:
            period_txt = 'periodo selecionado'
        order_txt = f"ordenado por {sort_by} ({'asc' if sort_asc else 'desc'})"
        summary = (
            f"Tabela de Trafego de Entrada por host (Minimo/Medio/Maximo em Mbps), {order_txt}. "
            f"Periodo: {period_txt}. Itens exibidos: {total_rows}."
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
        sort_by = (options.get('sort_by') or 'Avg')
        if sort_by not in {'Avg', 'Max', 'Min'}:
            sort_by = 'Avg'
        sort_asc = bool(options.get('sort_asc', False))
        raw_top = options.get('top_n')
        try:
            top_n = int(raw_top)
        except Exception:
            top_n = 5
        if top_n < 0:
            top_n = 0
        try:
            decimals = int(options.get('decimals') or 2)
        except Exception:
            decimals = 2
        if decimals < 0:
            decimals = 0
        show_summary = bool(options.get('show_summary', True))

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
            if sort_by in df_filtered.columns:
                try:
                    df_filtered = df_filtered.sort_values(by=sort_by, ascending=sort_asc)
                except Exception:
                    pass
            if top_n and top_n > 0:
                df_filtered = df_filtered.head(top_n)

        warning_text = base_message
        if df_filtered.empty:
            table_html = None
            if not warning_text:
                warning_text = 'Sem dados de trafego para os filtros informados.'
        else:
            df_format = df_filtered.copy()
            for column in ['Min', 'Avg', 'Max']:
                if column in df_format.columns:
                    df_format[column] = df_format[column].map(
                        lambda value: f"{float(value):.{decimals}f}" if pd.notna(value) else ''
                    )
            table_html = df_format.to_html(classes='table table-sm', index=False, escape=False)

        summary_text = None
        if show_summary:
            summary_text = self._format_summary(
                period_filtered,
                sort_by,
                sort_asc,
                len(df_filtered),
                top_n if top_n and top_n > 0 else None,
                interfaces_list,
            )

        if not table_html:
            table_html = '<p><i>Tabela de Trafego de Entrada indisponivel.</i></p>'

        if not self.module_config.get('title'):
            self.module_config['title'] = self.DEFAULT_TITLE

        return self.render('traffic_in_table', {
            'table_html': table_html,
            'summary_text': summary_text,
            'warning_text': warning_text,
        })
