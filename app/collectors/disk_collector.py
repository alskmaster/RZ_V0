import re
import pandas as pd
from flask import current_app
from .base_collector import BaseCollector
from app.charting import generate_multi_bar_chart
from app.collectors.robust_metric_engine import RobustMetricEngine
from app.models import MetricKeyProfile, CalculationType


class DiskCollector(BaseCollector):
    """
    Coleta resiliente de Disco:
    - Perfis + discovery; trends com fallback para history.
    - Seleciona, por host, o perfil preferido e o pior filesystem (maior média).
    """

    def collect(self, all_hosts, period):
        self._update_status("Coletando dados de Disco...")
        opts = self.module_config.get('custom_options', {}) or {}
        show_table = opts.get('show_table', True)
        show_chart = opts.get('show_chart', True)
        top_n = int(opts.get('top_n', 0) or 0)

        # Filtros de performance (surpresa boa):
        # - host_contains/limit_hosts reduzem hosts antes da coleta
        # - fs_selector root_only limita um FS por host (raiz ou unidade principal)
        host_contains = str(opts.get('host_contains') or '').strip()
        limit_hosts = int(opts.get('limit_hosts', 0) or 0)
        if host_contains:
            try:
                all_hosts = [h for h in all_hosts if host_contains.lower() in str(h.get('nome_visivel','')).lower()]
            except Exception:
                pass
        if limit_hosts > 0:
            all_hosts = all_hosts[:limit_hosts]

        engine = RobustMetricEngine(self.generator)
        filters = {
            'include_regex': opts.get('include_regex'),
            'exclude_regex': opts.get('exclude_regex'),
            'fs_selector': opts.get('fs_selector', 'root_only' if opts.get('fast_mode', True) else 'worst'),
            'percent_only': opts.get('percent_only', True),
            'chunk_size': int(opts.get('chunk_size')) if str(opts.get('chunk_size') or '').strip().isdigit() else None,
        }
        df_disk = engine.collect_disk_smart(all_hosts, period, filters=filters)
        if df_disk is None or df_disk.empty:
            # Fallback legado
            data, error_msg = self._collect_disk_data(all_hosts, period)
            if error_msg:
                return f"<p>Erro no módulo de Disco: {error_msg}</p>"
            df_disk = (data or {}).get('df_disk', pd.DataFrame())

        if df_disk.empty:
            return "<p><i>Não foram encontrados dados de disco para os hosts e período selecionados.</i></p>"

        module_data = {'tabela': None, 'grafico': None}
        if show_table:
            df_disk_table = df_disk.rename(columns={'Host': 'Host', 'Filesystem': 'Filesystem', 'Min': 'Mínimo (%)', 'Avg': 'Média (%)', 'Max': 'Máximo (%)'})
            module_data['tabela'] = df_disk_table.to_html(classes='table', index=False, float_format='%.2f')
        if show_chart:
            df_chart = df_disk.copy()
            if top_n > 0:
                df_chart = df_chart.sort_values(by='Avg', ascending=False).head(top_n)
            module_data['grafico'] = generate_multi_bar_chart(df_chart, 'Uso de Disco (%) - Pior FS por Host', 'Uso de Disco (%)', ['#d1b3ff', '#a366ff', '#7a1aff'])
        return self.render('disk', module_data)

    # Fallback legado (apenas perfis)
    def _collect_disk_data(self, all_hosts, period):
        try:
            host_ids = [h['hostid'] for h in all_hosts]
            host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}
            profiles = MetricKeyProfile.query.filter_by(metric_type='disk', is_active=True).order_by(MetricKeyProfile.priority).all()
            if not profiles:
                return None, "Nenhum perfil de métrica para 'disk' está ativo no banco de dados."

            current_app.logger.debug(f"[Disco fallback] {len(profiles)} perfis de chave encontrados.")
            all_disk_items = []
            for profile in profiles:
                items = self.generator.get_items(host_ids, profile.key_string, search_by_key=True)
                if items:
                    for it in items:
                        it['profile_calc_type'] = profile.calculation_type
                        it['profile_priority'] = profile.priority
                    all_disk_items.extend(items)
            if not all_disk_items:
                return None, "Nenhum item de Disco correspondente aos perfis configurados foi encontrado nos hosts."

            item_ids = [it['itemid'] for it in all_disk_items]
            disk_trends = self.generator.get_trends_with_fallback(item_ids, period['start'], period['end'], history_value_type=0)
            if not disk_trends:
                return {'df_disk': pd.DataFrame()}, None

            df = pd.DataFrame(disk_trends)
            df[['value_min', 'value_avg', 'value_max']] = df[['value_min', 'value_avg', 'value_max']].astype(float)
            item_map = {str(it['itemid']): it for it in all_disk_items}

            def _fs_from_key(key_):
                try:
                    m = re.search(r"vfs\.fs\.size\[(.*?),(.*?)\]", key_)
                    if m:
                        return m.group(1)
                except Exception:
                    pass
                return None

            df['itemid'] = df['itemid'].astype(str)
            df['hostid'] = df['itemid'].map(lambda x: item_map.get(x, {}).get('hostid'))
            df['fs_name'] = df['itemid'].map(lambda x: _fs_from_key(item_map.get(x, {}).get('key_', '')) or item_map.get(x, {}).get('name'))
            df['priority'] = df['itemid'].map(lambda x: item_map.get(x, {}).get('profile_priority', 9999))
            df['calc_type'] = df['itemid'].map(lambda x: item_map.get(x, {}).get('profile_calc_type', CalculationType.DIRECT))
            df.dropna(subset=['hostid', 'fs_name'], inplace=True)
            best = df.groupby('hostid')['priority'].transform('min')
            df = df[df['priority'] == best]

            rows = []
            for host_id, group in df.groupby('hostid'):
                agg_fs = group.groupby('fs_name')['value_avg'].mean().reset_index()
                if agg_fs.empty:
                    continue
                worst_fs = agg_fs.loc[agg_fs['value_avg'].idxmax(), 'fs_name']
                sel = group[group['fs_name'] == worst_fs]
                if sel.empty:
                    continue
                calc_type = sel['calc_type'].iloc[0]
                min_val = sel['value_min'].mean()
                avg_val = sel['value_avg'].mean()
                max_val = sel['value_max'].mean()
                if calc_type == CalculationType.INVERSE:
                    min_val, max_val = (100 - max_val), (100 - min_val)
                    avg_val = 100 - avg_val
                rows.append({'Host': host_map.get(host_id, f'Host {host_id}'), 'Filesystem': worst_fs, 'Min': float(min_val), 'Avg': float(avg_val), 'Max': float(max_val)})

            return {'df_disk': pd.DataFrame(rows)}, None

        except Exception as e:
            current_app.logger.error(f"[Disco fallback] Exceção inesperada - {e}", exc_info=True)
            return None, "Ocorreu uma falha inesperada durante a coleta de dados de disco."
