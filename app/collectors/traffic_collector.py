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
        host_ids = [h['hostid'] for h in all_hosts]
        host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}
        empty_df = pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max'])

        def get_traffic_data(key_filter):
            self._update_status(f"Buscando itens de trafego: {key_filter}")
            traffic_items = self.generator.get_items(host_ids, key_filter, search_by_key=True)

            if interfaces:
                regex = f".*({'|'.join(re.escape(i) for i in interfaces)})"
                traffic_items = [item for item in traffic_items if re.search(regex, item['key_'])]

            if not traffic_items:
                return empty_df.copy(), (
                    f"Nenhum item de trafego '{key_filter}' encontrado para as interfaces selecionadas."
                )

            item_ids = [item['itemid'] for item in traffic_items]
            chunk_size = int(self.module_config.get('trend_chunk_size') or 150)
            self._update_status(
                f"Buscando tendencias para {len(item_ids)} itens de trafego..."
            )
            traffic_trends = self.generator.get_trends_chunked(
                item_ids, period['start'], period['end'], chunk_size=chunk_size
            )
            if not traffic_trends:
                return empty_df.copy(), (
                    f"Nenhuma tendencia retornada para '{key_filter}'. Verifique a disponibilidade do Zabbix."
                )

            df_trends = pd.DataFrame(traffic_trends)
            required_cols = {'value_min', 'value_avg', 'value_max', 'itemid'}
            if not required_cols.issubset(df_trends.columns):
                return empty_df.copy(), (
                    f"Tendencias de '{key_filter}' retornaram um formato inesperado."
                )

            df_trends[['value_min', 'value_avg', 'value_max']] = df_trends[
                ['value_min', 'value_avg', 'value_max']
            ].astype(float)
            item_map = {str(item['itemid']): item['hostid'] for item in traffic_items}
            df_trends['itemid'] = df_trends['itemid'].astype(str)
            df_trends['hostid'] = df_trends['itemid'].map(item_map)
            df_trends.dropna(subset=['hostid'], inplace=True)
            if df_trends.empty:
                return empty_df.copy(), (
                    f"Nenhuma medida valida retornada para '{key_filter}'."
                )

            agg_functions = {
                'Min': ('value_min', 'sum'),
                'Avg': ('value_avg', 'sum'),
                'Max': ('value_max', 'sum'),
            }
            df_agg = df_trends.groupby('hostid').agg(**agg_functions).reset_index()
            if df_agg.empty:
                return empty_df.copy(), (
                    f"Nao foi possivel agregar dados de '{key_filter}'."
                )

            conversion = 8 / (1024 * 1024)
            for col in ['Min', 'Avg', 'Max']:
                df_agg[col] = df_agg[col] * conversion
            df_agg['Host'] = df_agg['hostid'].map(host_map)
            df_agg.dropna(subset=['Host'], inplace=True)
            if df_agg.empty:
                return empty_df.copy(), (
                    f"Nenhum host valido encontrado para '{key_filter}'."
                )
            df_agg = df_agg[['Host', 'Min', 'Avg', 'Max']].sort_values('Avg', ascending=False)
            df_agg.reset_index(drop=True, inplace=True)
            return df_agg, None

        df_net_in, error_in = get_traffic_data('net.if.in')
        df_net_out, error_out = get_traffic_data('net.if.out')

        data = {
            'df_net_in': df_net_in,
            'df_net_out': df_net_out,
            'messages': {
                'traffic_in': error_in,
                'traffic_out': error_out,
            },
        }

        return data, None
