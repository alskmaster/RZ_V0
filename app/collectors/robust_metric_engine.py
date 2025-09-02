import re
import pandas as pd
from flask import current_app
from app.models import CalculationType, MetricKeyProfile


class RobustMetricEngine:
    """
    Engine unificada e resiliente para coleta de CPU, Memória e Disco.
    - Usa perfis do banco quando disponíveis, com prioridade por host.
    - Faz descoberta oportunista de keys se os perfis não retornarem itens.
    - Consolida trends e, se necessário, faz fallback para history.get.
    - Normaliza cálculo (DIRECT vs INVERSE) e seleciona a melhor fonte por host.
    """

    def __init__(self, generator):
        self.g = generator  # ReportGenerator

    # ----------------------- Descoberta de Itens -----------------------

    def _discover_cpu_items(self, host_ids):
        cands = [
            ("system.cpu.util[,idle]", CalculationType.INVERSE, 1),
            ("system.cpu.util[,user]", CalculationType.DIRECT, 5),
            ("system.cpu.util", CalculationType.DIRECT, 3),
        ]
        items = []
        for key, calc, prio in cands:
            found = self.g.get_items(host_ids, key, search_by_key=True)
            for it in (found or []):
                it['profile_calc_type'] = calc
                it['profile_priority'] = prio
            items.extend(found or [])
        return items

    def _discover_mem_items(self, host_ids):
        cands = [
            ("vm.memory.size[pused]", CalculationType.DIRECT, 1),
            ("vm.memory.size[pavailable]", CalculationType.INVERSE, 2),
            ("vm.memory.size[pfree]", CalculationType.INVERSE, 2),
        ]
        items = []
        for key, calc, prio in cands:
            found = self.g.get_items(host_ids, key, search_by_key=True)
            for it in (found or []):
                it['profile_calc_type'] = calc
                it['profile_priority'] = prio
            items.extend(found or [])
        return items

    def _discover_disk_items(self, host_ids):
        # Busca genérica e deduz cálculo via key
        found = self.g.get_items(host_ids, 'vfs.fs.size', search_by_key=True)
        for it in (found or []):
            keyv = it.get('key_', '')
            if 'pused' in keyv:
                it['profile_calc_type'] = CalculationType.DIRECT
                it['profile_priority'] = 1
            elif 'pfree' in keyv or 'pavailable' in keyv:
                it['profile_calc_type'] = CalculationType.INVERSE
                it['profile_priority'] = 2
            else:
                # default conservador
                it['profile_calc_type'] = CalculationType.DIRECT
                it['profile_priority'] = 9
        return found or []

    def _items_from_profiles(self, host_ids, metric_type):
        items = []
        profiles = MetricKeyProfile.query.filter_by(metric_type=metric_type, is_active=True)\
            .order_by(MetricKeyProfile.priority.asc()).all()
        for p in profiles:
            found = self.g.get_items(host_ids, p.key_string, search_by_key=True)
            for it in (found or []):
                it['profile_calc_type'] = p.calculation_type
                it['profile_priority'] = p.priority
            items.extend(found or [])
        return items

    # ----------------------- CPU / MEM -----------------------

    def collect_cpu_or_mem(self, metric_type, all_hosts, period):
        host_ids = [h['hostid'] for h in all_hosts]
        host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}

        if metric_type not in {'cpu', 'memory'}:
            raise ValueError('metric_type inválido para collect_cpu_or_mem')

        # 1) Perfis do banco
        items = self._items_from_profiles(host_ids, 'cpu' if metric_type == 'cpu' else 'memory')
        # 2) Descoberta oportunista se vazio
        if not items:
            if metric_type == 'cpu':
                items = self._discover_cpu_items(host_ids)
            else:
                items = self._discover_mem_items(host_ids)

        if not items:
            return pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max'])

        item_ids = [it['itemid'] for it in items]
        trends = self.g.robust_aggregate(item_ids, period['start'], period['end'], items_meta=items)
        if not isinstance(trends, list) or not trends:
            return pd.DataFrame(columns=['Host', 'Min', 'Avg', 'Max'])

        df = pd.DataFrame(trends).astype({'itemid': str})
        items_map = {str(it['itemid']): it for it in items}

        df['hostid'] = df['itemid'].map(lambda x: items_map.get(x, {}).get('hostid'))
        df['priority'] = df['itemid'].map(lambda x: items_map.get(x, {}).get('profile_priority', 9999))
        df['calc_type'] = df['itemid'].map(lambda x: items_map.get(x, {}).get('profile_calc_type', CalculationType.DIRECT))
        df.dropna(subset=['hostid'], inplace=True)
        df['hostid'] = df['hostid'].astype(str)

        # Seleciona melhor perfil por host
        best = df.groupby('hostid')['priority'].transform('min')
        df = df[df['priority'] == best]

        # Agrega por host
        df[['value_min', 'value_avg', 'value_max']] = df[['value_min', 'value_avg', 'value_max']].astype(float)
        agg = df.groupby('hostid').agg(
            Min=('value_min', 'min'),
            Avg=('value_avg', 'mean'),
            Max=('value_max', 'max'),
            calc_type=('calc_type', 'first')
        ).reset_index()

        # Aplica inversão se necessário
        inv_mask = agg['calc_type'] == CalculationType.INVERSE
        agg.loc[inv_mask, ['Min', 'Max']] = 100.0 - agg.loc[inv_mask, ['Max', 'Min']].values
        agg.loc[inv_mask, 'Avg'] = 100.0 - agg.loc[inv_mask, 'Avg']

        agg['Host'] = agg['hostid'].map(host_map)
        result = agg[['Host', 'Min', 'Avg', 'Max']].copy()
        for c in ['Min', 'Avg', 'Max']:
            result[c] = pd.to_numeric(result[c], errors='coerce')
        return result.dropna(how='all', subset=['Min', 'Avg', 'Max']).reset_index(drop=True)

    # ----------------------- DISK -----------------------

    def collect_disk(self, all_hosts, period):
        host_ids = [h['hostid'] for h in all_hosts]
        host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}

        items = self._items_from_profiles(host_ids, 'disk')
        if not items:
            items = self._discover_disk_items(host_ids)
        if not items:
            return pd.DataFrame(columns=['Host', 'Filesystem', 'Min', 'Avg', 'Max'])

        item_ids = [it['itemid'] for it in items]
        trends = self.g.robust_aggregate(item_ids, period['start'], period['end'], items_meta=items)
        if not isinstance(trends, list) or not trends:
            return pd.DataFrame(columns=['Host', 'Filesystem', 'Min', 'Avg', 'Max'])

        df = pd.DataFrame(trends)
        df[['value_min', 'value_avg', 'value_max']] = df[['value_min', 'value_avg', 'value_max']].astype(float)
        items_map = {str(it['itemid']): it for it in items}

        def _fs_from_key(key_: str):
            try:
                m = re.search(r"vfs\.fs\.size\[(.*?),(.*?)\]", key_)
                if m:
                    return m.group(1)
            except Exception:
                pass
            return None

        df['itemid'] = df['itemid'].astype(str)
        df['hostid'] = df['itemid'].map(lambda x: items_map.get(x, {}).get('hostid'))
        df['fs_name'] = df['itemid'].map(lambda x: _fs_from_key(items_map.get(x, {}).get('key_', '')) or items_map.get(x, {}).get('name'))
        df['priority'] = df['itemid'].map(lambda x: items_map.get(x, {}).get('profile_priority', 9999))
        df['calc_type'] = df['itemid'].map(lambda x: items_map.get(x, {}).get('profile_calc_type', CalculationType.DIRECT))
        df.dropna(subset=['hostid', 'fs_name'], inplace=True)

        # Seleciona melhor perfil por host
        best = df.groupby('hostid')['priority'].transform('min')
        df = df[df['priority'] == best]

        # Por host, escolher o FS com maior média de uso (pior)
        final_rows = []
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
            final_rows.append({
                'Host': host_map.get(host_id, f'Host {host_id}'),
                'Filesystem': worst_fs,
                'Min': float(min_val),
                'Avg': float(avg_val),
                'Max': float(max_val),
            })
        if not final_rows:
            return pd.DataFrame(columns=['Host', 'Filesystem', 'Min', 'Avg', 'Max'])
        return pd.DataFrame(final_rows, columns=['Host', 'Filesystem', 'Min', 'Avg', 'Max'])
