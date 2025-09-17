import hashlib
import json
import re
from typing import Tuple

import pandas as pd
from flask import current_app

from .robust_metric_engine import RobustMetricEngine
from app.models import MetricKeyProfile, CalculationType


def _filter_hosts(all_hosts, host_contains: str, limit_hosts: int):
    hosts = list(all_hosts or [])
    if host_contains:
        try:
            hosts = [h for h in hosts if host_contains.lower() in str(h.get('nome_visivel', '')).lower()]
        except Exception:
            pass
    if limit_hosts and limit_hosts > 0:
        hosts = hosts[:limit_hosts]
    return hosts


def _fallback_disk_dataframe(generator, hosts, period) -> Tuple[pd.DataFrame, str]:
    try:
        host_ids = [h['hostid'] for h in hosts]
        host_map = {h['hostid']: h['nome_visivel'] for h in hosts}
        profiles = (MetricKeyProfile.query
                    .filter_by(metric_type='disk', is_active=True)
                    .order_by(MetricKeyProfile.priority)
                    .all())
        if not profiles:
            return pd.DataFrame(), "Nenhum perfil de métrica para 'disk' está ativo no banco."

        current_app.logger.debug(f"[Disco fallback] {len(profiles)} perfis de chave encontrados.")
        all_disk_items = []
        for profile in profiles:
            items = generator.get_items(host_ids, profile.key_string, search_by_key=True)
            if items:
                for it in items:
                    it['profile_calc_type'] = profile.calculation_type
                    it['profile_priority'] = profile.priority
                all_disk_items.extend(items)
        if not all_disk_items:
            return pd.DataFrame(), "Nenhum item de Disco correspondente aos perfis configurados foi encontrado nos hosts."

        item_ids = [it['itemid'] for it in all_disk_items]
        disk_trends = generator.get_trends_with_fallback(item_ids, period['start'], period['end'], history_value_type=0)
        if not disk_trends:
            return pd.DataFrame(), None

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
        if df.empty:
            return pd.DataFrame(), "Nenhum filesystem válido retornado para os hosts selecionados."

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
            rows.append({
                'Host': host_map.get(host_id, f'Host {host_id}'),
                'Filesystem': worst_fs,
                'Min': float(min_val),
                'Avg': float(avg_val),
                'Max': float(max_val)
            })

        return pd.DataFrame(rows), None
    except Exception as exc:
        current_app.logger.error(f"[Disco fallback] Exceção inesperada - {exc}", exc_info=True)
        return pd.DataFrame(), "Falha inesperada durante a coleta de dados de disco (fallback)."


def collect_disk_dataframe(generator, module_config, all_hosts, period) -> Tuple[pd.DataFrame, str]:
    opts = module_config.get('custom_options', {}) or {}
    host_contains = str(opts.get('host_contains') or '').strip()
    limit_hosts = int(opts.get('limit_hosts') or 0)
    hosts = _filter_hosts(all_hosts, host_contains, limit_hosts)

    filters = {
        'include_regex': opts.get('include_regex') or None,
        'exclude_regex': opts.get('exclude_regex') or None,
        'fs_selector': opts.get('fs_selector') or ('root_only' if opts.get('fast_mode', True) else 'worst'),
        'percent_only': opts.get('percent_only', True),
        'chunk_size': int(opts.get('chunk_size')) if str(opts.get('chunk_size') or '').strip().isdigit() else None,
        'per_host_limit': int(opts.get('per_host_limit') or 0) or None,
    }

    cache_bucket = generator.cached_data.setdefault('disk_shared', {})
    key_payload = {
        'host_ids': [h.get('hostid') for h in hosts],
        'period': [int(period.get('start') or 0), int(period.get('end') or 0)],
        'filters': filters,
    }
    cache_key = 'disk::' + hashlib.md5(json.dumps(key_payload, sort_keys=True, default=str).encode()).hexdigest()

    if cache_key not in cache_bucket:
        engine = RobustMetricEngine(generator)
        df = engine.collect_disk_smart(hosts, period, filters=filters)
        if df is None:
            df = pd.DataFrame(columns=['Host', 'Filesystem', 'Min', 'Avg', 'Max'])
        elif not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        warning = None
        if df.empty:
            fallback_df, fallback_warning = _fallback_disk_dataframe(generator, hosts, period)
            df = fallback_df
            warning = fallback_warning
        cache_bucket[cache_key] = {
            'df': df.copy(),
            'warning': warning
        }

    cached = cache_bucket[cache_key]
    df_ret = cached['df'].copy()
    warning_text = cached.get('warning')
    return df_ret, warning_text
