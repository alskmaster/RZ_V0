from flask import request, jsonify, current_app
import datetime as dt

from . import admin
from app.utils import admin_required
from app import db
from app.models import Client, MetricKeyProfile
from app.services import ReportGenerator
from app.zabbix_api import obter_config_e_token_zabbix


@admin.route('/debug_collect')
@admin_required
def debug_collect():
    """Diagnóstico de coleta para módulos CPU/MEM/DISK.

    Parâmetros:
      - client_id (int)
      - module (str): cpu | mem | disk
      - mes_ref (str, opcional): YYYY-MM (padrão: mês atual)
    Retorna estatísticas sobre hosts, itens encontrados por perfil e pontos de dados.
    """
    client_id = request.args.get('client_id', type=int)
    module = (request.args.get('module') or '').strip()
    mes_ref = (request.args.get('mes_ref') or '').strip()
    if module not in {'cpu', 'mem', 'disk'} or not client_id:
        return jsonify({'error': 'Parâmetros inválidos.'}), 400

    metric_type = {'cpu': 'cpu', 'mem': 'memory', 'disk': 'disk', 'wifi': 'wifi_clients'}.get(module)
    if not metric_type:
        return jsonify({'error': 'Módulo inválido.'}), 400

    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({'error': 'Cliente não encontrado.'}), 404

    # Período
    try:
        if mes_ref:
            ref_date = dt.datetime.strptime(f'{mes_ref}-01', '%Y-%m-%d')
        else:
            today = dt.date.today()
            ref_date = dt.datetime(today.year, today.month, 1)
    except ValueError:
        return jsonify({'error': 'mes_ref inválido, use YYYY-MM.'}), 400
    start_date = ref_date.replace(day=1, hour=0, minute=0, second=0)
    end_date = (start_date.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(seconds=1)
    period = {'start': int(start_date.timestamp()), 'end': int(end_date.timestamp())}

    # Conexão com Zabbix
    config_zabbix, erro = obter_config_e_token_zabbix(current_app.config)
    if erro:
        return jsonify({'error': f'Falha ao conectar ao Zabbix: {erro}'}), 502
    generator = ReportGenerator(config_zabbix, 'debug_task')

    # Hosts pelos grupos do cliente
    try:
        group_ids = [g.group_id for g in client.zabbix_groups.all()]
    except Exception:
        group_ids = []
    hosts = generator.get_hosts(group_ids)
    if not hosts:
        return jsonify({'error': 'Nenhum host nos grupos do cliente.'}), 404
    host_ids = [h['hostid'] for h in hosts]

    # Perfis ativos
    profiles = (MetricKeyProfile.query
                .filter_by(metric_type=metric_type, is_active=True)
                .order_by(MetricKeyProfile.priority.asc())
                .all())

    prof_stats = []
    all_items = []
    for p in profiles:
        items = generator.get_items(host_ids, p.key_string, search_by_key=True)
        prof_stats.append({
            'key_string': p.key_string,
            'calculation_type': getattr(p.calculation_type, 'name', str(p.calculation_type)),
            'priority': p.priority,
            'found': len(items),
            'examples': [it.get('key_') for it in (items[:3] or [])]
        })
        all_items.extend(items)

    item_ids = [it['itemid'] for it in all_items]
    data_points = 0
    if item_ids:
        if module == 'wifi':
            # unsigned counters usually
            trends = generator.robust_aggregate(item_ids, period['start'], period['end'], items_meta=all_items)
        else:
            trends = generator.robust_aggregate(item_ids, period['start'], period['end'], items_meta=all_items)
        data_points = len(trends) if isinstance(trends, list) else 0

    return jsonify({
        'client': {'id': client.id, 'name': client.name},
        'module': module,
        'period': period,
        'hosts': len(hosts),
        'profiles': prof_stats,
        'total_items': len(all_items),
        'data_points': data_points
    })
