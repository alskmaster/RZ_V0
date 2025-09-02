import pandas as pd
from flask import current_app
from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart
from app.collectors.robust_metric_engine import RobustMetricEngine
from app.models import MetricKeyProfile, CalculationType
from rz_debug import with_debug


class MemCollector(BaseCollector):
    """
    Coleta resiliente de Memória:
    - Perfis + discovery; trends com fallback para history.
    - Seleção por host do melhor perfil (prioridade).
    """

    @with_debug
    def collect(self, all_hosts, period):
        current_app.logger.debug("[Memória] Iniciando coleta (engine resiliente)")
        self._update_status("Coletando dados de Memória...")

        opts = self.module_config.get('custom_options', {})
        show_table = opts.get('show_table', True)
        show_chart = opts.get('show_chart', True)
        top_n = opts.get('top_n', 0)

        engine = RobustMetricEngine(self.generator)
        df_mem = engine.collect_cpu_or_mem('memory', all_hosts, period)
        if df_mem is None or df_mem.empty:
            # Fallback legado
            data, error_msg = self._collect_mem_data(all_hosts, period)
            if error_msg:
                current_app.logger.error(f"[Memória] Erro durante a coleta (fallback) - {error_msg}")
                return f"<p>Erro no módulo de Memória: {error_msg}</p>"
            df_mem = (data or {}).get('df_mem')

        if df_mem is None or df_mem.empty:
            return "<p><i>Não foram encontrados dados de memória para os hosts e período selecionados.</i></p>"

        module_data = {'tabela': None, 'grafico': None}
        if show_table:
            module_data['tabela'] = df_mem.to_html(classes='table', index=False, float_format='%.2f')
        if show_chart:
            df_chart = df_mem.copy()
            if top_n > 0:
                df_chart = df_chart.sort_values(by='Avg', ascending=False).head(top_n)
            module_data['grafico'] = generate_multi_bar_chart(
                df_chart,
                'Uso de Memória (%)',
                'Uso de Memória (%)',
                ['#66b3ff', '#3385ff', '#0047b3']
            )
        return self.render('mem', module_data)

    # Fallback legado (apenas perfis)
    def _collect_mem_data(self, all_hosts, period):
        try:
            host_ids = [h['hostid'] for h in all_hosts]
            host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}
            profiles = MetricKeyProfile.query.filter_by(metric_type='memory', is_active=True).order_by(MetricKeyProfile.priority).all()
            if not profiles:
                return None, "Nenhum perfil de métrica para 'memory' está ativo no banco de dados."
            current_app.logger.debug(f"[Memória fallback] {len(profiles)} perfis de chave encontrados.")

            all_mem_items = []
            for profile in profiles:
                items = self.generator.get_items(host_ids, profile.key_string, search_by_key=True)
                if items:
                    for item in items:
                        item['profile_calc_type'] = profile.calculation_type
                        item['profile_priority'] = profile.priority
                    all_mem_items.extend(items)
            if not all_mem_items:
                return None, "Nenhum item de memória correspondente aos perfis configurados foi encontrado nos hosts."

            item_ids = [item['itemid'] for item in all_mem_items]
            mem_trends = self.generator.get_trends_with_fallback(item_ids, period['start'], period['end'], history_value_type=0)
            if not mem_trends:
                return None, "Nenhum dado de histórico (trends) encontrado para os itens de memória."

            df_trends = pd.DataFrame(mem_trends).astype({'itemid': str})
            items_map = {str(item['itemid']): item for item in all_mem_items}
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
                return None, "Dados de histórico de memória não puderam ser processados."

            df_mem = pd.DataFrame(rows, columns=['Host', 'Min', 'Avg', 'Max'])
            for c in ['Min', 'Avg', 'Max']:
                df_mem[c] = pd.to_numeric(df_mem[c], errors='coerce')
            return {'df_mem': df_mem.dropna(how='all', subset=['Min', 'Avg', 'Max']).reset_index(drop=True)}, None

        except Exception as e:
            current_app.logger.error(f"[Memória fallback] Exceção inesperada - {e}", exc_info=True)
            return None, "Ocorreu uma falha inesperada durante a coleta de dados de memória."

