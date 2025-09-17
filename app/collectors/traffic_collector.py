# app/collectors/traffic_collector.py
import pandas as pd
from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart
import re


class TrafficCollector(BaseCollector):
    """Collector para os modulos de trafego de entrada e saida."""

    def collect(self, all_hosts, period):
        interfaces = self.module_config.get('interfaces', [])
        interfaces_key = '_'.join(sorted(interfaces)) if interfaces else 'all'
        cache_key = f"traffic_data_{interfaces_key}"

        if cache_key not in self.generator.cached_data:
            self._update_status(
                f"Coletando dados de Trafego para interfaces: {interfaces_key}..."
            )
            data, error_msg = self._collect_traffic_data(all_hosts, period, interfaces)
            if error_msg:
                return f"<p>Erro no modulo de Trafego: {error_msg}</p>"
            self.generator.cached_data[cache_key] = data

        cached = self.generator.cached_data.get(cache_key, {})
        module_type = self.module_config.get('type')
        title_suffix = ''
        if len(interfaces) > 1:
            title_suffix = f" - Agregado ({', '.join(interfaces)})"
        elif interfaces:
            title_suffix = f" - {interfaces[0]}"

        if module_type == 'traffic_in':
            df = cached.get('df_net_in', pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max']))
            title = self.module_config.get('title') or f"Trafego de Entrada (Mbps){title_suffix}"
            chart_title = 'Trafego de Entrada (Mbps)'
            colors = ['#ffc266', '#ffa31a', '#e68a00']
        else:
            df = cached.get('df_net_out', pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max']))
            title = self.module_config.get('title') or f"Trafego de Saida (Mbps){title_suffix}"
            chart_title = 'Trafego de Saida (Mbps)'
            colors = ['#85e085', '#33cc33', '#248f24']

        messages = cached.get('messages', {})
        module_message = messages.get(module_type)

        table_html, chart_image, message = self._build_outputs(
            df, chart_title, colors, module_message
        )

        self.module_config['title'] = title
        return self.render('traffic', {
            'tabela': table_html,
            'grafico': chart_image,
            'mensagem': message,
        })

    def _build_outputs(self, df, chart_title, colors, module_message=None):
        df = df.copy()
        if df.empty:
            message = module_message or 'Sem dados de trafego disponiveis para o periodo selecionado.'
            return None, None, message

        df[['Min', 'Avg', 'Max']] = df[['Min', 'Avg', 'Max']].astype(float)
        df[['Min', 'Avg', 'Max']] = df[['Min', 'Avg', 'Max']].round(4)
        table_html = df.to_html(classes='table table-sm', index=False, border=0)
        chart_image = generate_multi_bar_chart(df, chart_title, 'Mbps', colors)
        return table_html, chart_image, module_message

    def _collect_traffic_data(self, all_hosts, period, interfaces):
        interfaces = interfaces or []
        try:
            chunk_size = int(self.module_config.get('trend_chunk_size') or 150)
        except Exception:
            chunk_size = 150

        df_net_in, error_in = self.generator.shared_collect_traffic(
            all_hosts, period, 'net.if.in', interfaces=interfaces, chunk_size=chunk_size
        )
        df_net_out, error_out = self.generator.shared_collect_traffic(
            all_hosts, period, 'net.if.out', interfaces=interfaces, chunk_size=chunk_size
        )

        if error_in and error_out:
            return None, f"{error_in} e {error_out}"
        if error_in and df_net_out is not None and not df_net_out.empty:
            return None, error_in
        if error_out and df_net_in is not None and not df_net_in.empty:
            return None, error_out

        data = {
            'df_net_in': df_net_in,
            'df_net_out': df_net_out,
            'messages': {
                'traffic_in': error_in,
                'traffic_out': error_out,
            },
        }

        return data, None

