# app/collectors/disk_collector.py
import pandas as pd
from flask import current_app
from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart
# --- MODIFICAÇÃO: Importa o modelo de Perfil de Métrica ---
from app.models import MetricKeyProfile, CalculationType

class DiskCollector(BaseCollector):
    """
    Plugin (Collector) para coletar e renderizar dados de Disco.
    - Suporta opções customizadas (show_table, show_chart, top_n).
    - Usa Perfis de Métrica para buscar chaves dinamicamente.
    """
    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de Disco...")

        opts = self.module_config.get('custom_options', {})
        show_table = opts.get('show_table', True)
        show_chart = opts.get('show_chart', True)
        top_n = opts.get('top_n', 0)

        data, error_msg = self._collect_disk_data(all_hosts, period)
        if error_msg:
            return f"<p>Erro no módulo de Disco: {error_msg}</p>"

        df_disk = data['df_disk']

        if df_disk.empty:
            return "<p><i>Não foram encontrados dados de disco para os hosts e período selecionados.</i></p>"

        module_data = {
            'tabela': None,
            'grafico': None
        }

        if show_table:
            df_disk_table = df_disk.rename(columns={
                'Host': 'Host', 'Filesystem': 'Filesystem', 'Min': 'Mínimo (%)',
                'Max': 'Máximo (%)', 'Avg': 'Média (%)'
            })
            module_data['tabela'] = df_disk_table.to_html(classes='table', index=False, float_format='%.2f')

        if show_chart:
            df_chart = df_disk.copy()
            if top_n > 0:
                df_chart = df_chart.sort_values(by='Avg', ascending=False).head(top_n)

            module_data['grafico'] = generate_multi_bar_chart(
                df_chart, 'Uso de Disco (%) - Pior FS por Host', 'Uso de Disco (%)',
                ['#d1b3ff', '#a366ff', '#7a1aff']
            )

        return self.render('disk', module_data)

    def _collect_disk_data(self, all_hosts, period):
        """
        Coleta e processa dados de Disco do Zabbix usando Perfis de Métrica.
        """
        try:
            host_ids = [h['hostid'] for h in all_hosts]
            host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}

            # --- MODIFICAÇÃO PRINCIPAL: Busca dinâmica de chaves ---
            profiles = MetricKeyProfile.query.filter_by(metric_type='disk', is_active=True).order_by(MetricKeyProfile.priority).all()
            if not profiles:
                return None, "Nenhum perfil de métrica para 'disk' está ativo no banco de dados."

            current_app.logger.debug(f"Módulo Disco [Dinâmico]: {len(profiles)} perfis de chave encontrados.")

            all_disk_items = []
            for profile in profiles:
                items = self.generator.get_items(host_ids, profile.key_string, search_by_key=True)
                if items:
                    for item in items:
                        # Associa o tipo de cálculo do perfil ao item encontrado
                        item['profile_calc_type'] = profile.calculation_type
                    all_disk_items.extend(items)

            if not all_disk_items:
                return None, "Nenhum item de Disco correspondente aos perfis configurados foi encontrado nos hosts."

            current_app.logger.debug(f"Módulo Disco [Dinâmico]: {len(all_disk_items)} itens de disco encontrados no total.")

            item_ids = [item['itemid'] for item in all_disk_items]
            disk_trends = self.generator.get_trends(item_ids, period['start'], period['end'])

            if not disk_trends:
                return {'df_disk': pd.DataFrame()}, None

            df_trends = pd.DataFrame(disk_trends)
            df_trends[['value_min', 'value_avg', 'value_max']] = df_trends[['value_min', 'value_avg', 'value_max']].astype(float)
            
            item_map = {str(item['itemid']): item for item in all_disk_items}
            df_trends['hostid'] = df_trends['itemid'].map(lambda x: item_map.get(str(x), {}).get('hostid'))
            df_trends['fs_name'] = df_trends['itemid'].map(lambda x: item_map.get(str(x), {}).get('name'))
            df_trends['calc_type'] = df_trends['itemid'].map(lambda x: item_map.get(str(x), {}).get('profile_calc_type', CalculationType.DIRECT))
            df_trends.dropna(subset=['hostid', 'fs_name'], inplace=True)
            
            # --- Lógica para achar o pior filesystem (maior uso) por host ---
            final_data = []
            grouped_by_host = df_trends.groupby('hostid')

            for host_id, group in grouped_by_host:
                # Calcula a média de uso para cada filesystem deste host
                agg_fs = group.groupby('fs_name').agg(Avg=('value_avg', 'mean')).reset_index()
                if agg_fs.empty:
                    continue

                # Encontra o filesystem com a maior média de uso
                worst_fs_name = agg_fs.loc[agg_fs['Avg'].idxmax()]['fs_name']
                
                # Filtra as tendências apenas para este filesystem
                host_fs_trends = group[group['fs_name'] == worst_fs_name]
                
                if not host_fs_trends.empty:
                    calc_type = host_fs_trends['calc_type'].iloc[0]
                    min_val = host_fs_trends['value_min'].mean()
                    avg_val = host_fs_trends['value_avg'].mean()
                    max_val = host_fs_trends['value_max'].mean()
                    
                    # Aplica cálculo inverso se necessário (ex: monitorando espaço livre)
                    if calc_type == CalculationType.INVERSE:
                        min_val, max_val = (100 - max_val), (100 - min_val)
                        avg_val = 100 - avg_val
                    
                    final_data.append({
                        'Host': host_map.get(host_id),
                        'Filesystem': worst_fs_name,
                        'Min': min_val,
                        'Max': max_val,
                        'Avg': avg_val
                    })

            return {'df_disk': pd.DataFrame(final_data)}, None

        except Exception as e:
            current_app.logger.error(f"Módulo Disco [Dinâmico]: Exceção inesperada - {e}", exc_info=True)
            return None, "Ocorreu uma falha inesperada durante a coleta de dados de disco."