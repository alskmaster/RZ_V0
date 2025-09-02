import pandas as pd
from flask import current_app
from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart
from app.collectors.robust_metric_engine import RobustMetricEngine
from app.models import MetricKeyProfile, CalculationType


class CpuCollector(BaseCollector):
    """
    Coleta resiliente de CPU:
    - Tenta perfis + discovery; usa trends e fallback para history.
    - Seleciona, por host, o melhor perfil disponível (menor prioridade numérica).
    """

    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de CPU...")

        opts = self.module_config.get('custom_options', {})
        show_table = opts.get('show_table', True)
        show_chart = opts.get('show_chart', True)
        top_n = opts.get('top_n', 0)

        engine = RobustMetricEngine(self.generator)
        df_cpu = engine.collect_cpu_or_mem('cpu', all_hosts, period)
        if df_cpu is None or df_cpu.empty:
            # Fallback: caminho anterior baseado apenas em perfis
            data, error_msg = self._collect_cpu_data(all_hosts, period)
            if error_msg:
                return f"<p>Erro no módulo de CPU: {error_msg}</p>"
            df_cpu = (data or {}).get('df_cpu')

        if df_cpu is None or df_cpu.empty:
            return "<p><i>Não foram encontrados dados de CPU para os hosts e período selecionados.</i></p>"

        module_data = {
            'tabela': None,
            'grafico': None
        }
        if show_table:
            module_data['tabela'] = df_cpu.to_html(classes='table', index=False, float_format='%.2f')

        if show_chart:
            df_chart = df_cpu.copy()
            if top_n > 0:
                df_chart = df_chart.sort_values(by='Avg', ascending=False).head(top_n)

            module_data['grafico'] = generate_multi_bar_chart(
                df_chart,
                'Ocupação de CPU (%)',
                'Uso de CPU (%)',
                ['#ff9999', '#ff4d4d', '#cc0000']
            )

        return self.render('cpu', module_data)

    # Fallback legado (só perfis)
    def _collect_cpu_data(self, all_hosts, period):
        try:
            host_ids = [h['hostid'] for h in all_hosts]
            host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}

            profiles = MetricKeyProfile.query.filter_by(metric_type='cpu', is_active=True).order_by(MetricKeyProfile.priority).all()
            if not profiles:
                return None, "Nenhum perfil de métrica para 'cpu' está ativo no banco de dados."

            current_app.logger.debug(f"[CPU fallback] {len(profiles)} perfis de chave encontrados.")

            all_cpu_items = []
            for profile in profiles:
                items = self.generator.get_items(host_ids, profile.key_string, search_by_key=True)
                if items:
                    for item in items:
                        item['profile_calc_type'] = profile.calculation_type
                        item['profile_priority'] = profile.priority
                    all_cpu_items.extend(items)

            if not all_cpu_items:
                return None, "Nenhum item de CPU correspondente aos perfis configurados foi encontrado nos hosts."

            item_ids = [item['itemid'] for item in all_cpu_items]
            cpu_trends = self.generator.get_trends_with_fallback(item_ids, period['start'], period['end'], history_value_type=0)
            if not cpu_trends:
                return {'df_cpu': pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max'])}, None

            df_cpu = self._process_trends_dynamic(cpu_trends, all_cpu_items, host_map)
            return {'df_cpu': df_cpu}, None

        except Exception as e:
            current_app.logger.error(f"[CPU fallback] Exceção inesperada - {e}", exc_info=True)
            return None, "Ocorreu uma falha inesperada durante a coleta de dados de CPU."

    def _process_trends_dynamic(self, trends, items, host_map):
        if not trends or not items:
            return pd.DataFrame()
        df_trends = pd.DataFrame(trends).astype({'itemid': str})
        items_map = {str(item['itemid']): item for item in items}
        df_trends['hostid'] = df_trends['itemid'].map(lambda x: items_map.get(x, {}).get('hostid'))
        df_trends.dropna(subset=['hostid'], inplace=True)
        df_trends['hostid'] = df_trends['hostid'].astype(str)
        df_trends['priority'] = df_trends['itemid'].map(lambda x: items_map.get(x, {}).get('profile_priority', 9999))
        _best = df_trends.groupby('hostid')['priority'].transform('min')
        df_trends = df_trends[df_trends['priority'] == _best]

        rows = []
        for host_id, group in df_trends.groupby('hostid'):
            hid = str(host_id)
            first_item_id = group['itemid'].iloc[0]
            calc_type = items_map.get(first_item_id, {}).get('profile_calc_type', CalculationType.DIRECT)
            min_val = group['value_min'].astype(float).min()
            avg_val = group['value_avg'].astype(float).mean()
            max_val = group['value_max'].astype(float).max()
            if calc_type == CalculationType.INVERSE:
                min_val, max_val = (100 - max_val), (100 - min_val)
                avg_val = 100 - avg_val
            rows.append({'Host': host_map.get(hid, f'Host {hid}'), 'Min': float(min_val), 'Avg': float(avg_val), 'Max': float(max_val)})

        if not rows:
            return pd.DataFrame()
        out = pd.DataFrame(rows, columns=['Host', 'Min', 'Avg', 'Max'])
        for c in ['Min', 'Avg', 'Max']:
            out[c] = pd.to_numeric(out[c], errors='coerce')
        return out.dropna(how='all', subset=['Min', 'Avg', 'Max']).reset_index(drop=True)

