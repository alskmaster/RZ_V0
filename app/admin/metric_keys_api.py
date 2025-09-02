# app/admin/metric_keys_api.py
from flask import request, jsonify, current_app, g

from app import db
from app.models import Client, MetricKeyProfile, CalculationType
from app.zabbix_api import obter_config_e_token_zabbix, fazer_request_zabbix

from . import admin
from app.utils import admin_required


@admin.route('/metric_keys/clients')
@admin_required
def metric_keys_clients():
    """Lista simples de clientes (JSON) para o assistente de descoberta."""
    try:
        clients = Client.query.order_by(Client.name.asc()).all()
        data = [{'id': c.id, 'name': c.name} for c in clients]
        return jsonify({'clients': data})
    except Exception as e:
        current_app.logger.error(f"[{getattr(g, 'request_id', '-')}] Erro ao listar clientes: {e}", exc_info=True)
        return jsonify({'clients': []}), 500


@admin.route('/metric_keys/discover')
@admin_required
def discover_metric_keys():
    """Descobre chaves candidatas no Zabbix para um cliente e tipo de métrica.

    Query params:
      - client_id: ID do cliente
      - metric_type: 'memory' | 'cpu' | 'disk'
    """
    client_id = request.args.get('client_id', type=int)
    metric_type = (request.args.get('metric_type') or '').strip()

    if not client_id or metric_type not in {'memory', 'cpu', 'disk', 'wifi_clients'}:
        return jsonify({'error': 'Parâmetros inválidos.'}), 400

    client = db.session.get(Client, client_id)
    if not client or client.zabbix_groups.count() == 0:
        return jsonify({'candidates': []})

    group_ids = [g.group_id for g in client.zabbix_groups.all()]

    config_zabbix, erro = obter_config_e_token_zabbix(current_app.config)
    if erro:
        return jsonify({'error': f'Falha ao conectar ao Zabbix: {erro}'}), 502

    # Hosts do cliente
    body_hosts = {
        'jsonrpc': '2.0',
        'method': 'host.get',
        'params': {'groupids': group_ids, 'output': ['hostid']},
        'auth': config_zabbix['ZABBIX_TOKEN'],
        'id': 1
    }
    hosts = fazer_request_zabbix(body_hosts, config_zabbix['ZABBIX_URL'])
    if not isinstance(hosts, list) or not hosts:
        return jsonify({'candidates': []})
    hostids = [h['hostid'] for h in hosts]

    def _count_items_by_key_pattern(key_pattern: str) -> int:
        body_item = {
            'jsonrpc': '2.0',
            'method': 'item.get',
            'params': {
                'hostids': hostids,
                'search': {'key_': key_pattern},
                'countOutput': True
            },
            'auth': config_zabbix['ZABBIX_TOKEN'],
            'id': 1
        }
        res = fazer_request_zabbix(body_item, config_zabbix['ZABBIX_URL'])
        try:
            return int(res)
        except Exception:
            return 0

    candidates = []

    if metric_type == 'memory':
        defs = [
            ('vm.memory.size[pused]', 'DIRECT'),
            ('vm.memory.size[pavailable]', 'INVERSE'),
            ('vm.memory.size[pfree]', 'INVERSE')
        ]
        for key_pattern, calc in defs:
            cnt = _count_items_by_key_pattern(key_pattern)
            if cnt > 0:
                candidates.append({'key_string': key_pattern, 'suggested_calc_type': calc, 'found_count': cnt})

    elif metric_type == 'cpu':
        defs = [
            ('system.cpu.util[,idle]', 'INVERSE'),
            ('system.cpu.util[,user]', 'DIRECT'),
            ('system.cpu.util', 'DIRECT')
        ]
        for key_pattern, calc in defs:
            cnt = _count_items_by_key_pattern(key_pattern)
            if cnt > 0:
                candidates.append({'key_string': key_pattern, 'suggested_calc_type': calc, 'found_count': cnt})

    elif metric_type == 'disk':
        # Busca todas as keys de fs e conta pused/pfree
        body_items = {
            'jsonrpc': '2.0',
            'method': 'item.get',
            'params': {
                'hostids': hostids,
                'output': ['key_'],
                'search': {'key_': 'vfs.fs.size'}
            },
            'auth': config_zabbix['ZABBIX_TOKEN'],
            'id': 1
        }
        items = fazer_request_zabbix(body_items, config_zabbix['ZABBIX_URL'])
        cnt_used = 0
        cnt_free = 0
        if isinstance(items, list):
            for it in items:
                k = it.get('key_', '')
                if 'pused' in k:
                    cnt_used += 1
                if 'pfree' in k or 'pavailable' in k:
                    cnt_free += 1
        if cnt_used > 0:
            candidates.append({'key_string': 'vfs.fs.size', 'suggested_calc_type': 'DIRECT', 'found_count': cnt_used})
        if cnt_free > 0:
            candidates.append({'key_string': 'vfs.fs.size', 'suggested_calc_type': 'INVERSE', 'found_count': cnt_free})

    elif metric_type == 'wifi_clients':
        # Chaves comuns de contagem de clientes Wi‑Fi (vendors variados)
        wifi_defs = [
            ('clientcountnumber', 'DIRECT'),
            ('wlan.bss.numsta', 'DIRECT'),
            ('StationsConnected', 'DIRECT'),
            ('wlan.client.count', 'DIRECT'),
        ]
        for key_pattern, calc in wifi_defs:
            cnt = _count_items_by_key_pattern(key_pattern)
            if cnt > 0:
                candidates.append({'key_string': key_pattern, 'suggested_calc_type': calc, 'found_count': cnt})

    # Marca os que já existem (mesma key + cálculo) para evitar duplicatas
    existing = MetricKeyProfile.query.filter_by(metric_type=metric_type).all()
    existing_set = {(e.key_string, (e.calculation_type.name if hasattr(e.calculation_type, 'name') else str(e.calculation_type))) for e in existing}
    for c in candidates:
        c['exists'] = (c['key_string'], c.get('suggested_calc_type')) in existing_set

    candidates = sorted(candidates, key=lambda x: x['found_count'], reverse=True)
    return jsonify({'candidates': candidates})


@admin.route('/metric_keys/bulk_add', methods=['POST'])
@admin_required
def bulk_add_metric_keys():
    """Cadastra múltiplos perfis de métricas em lote (JSON)."""
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        return jsonify({'error': 'JSON inválido.'}), 400

    metric_type = (data.get('metric_type') or '').strip()
    items = data.get('items') or []
    if metric_type not in {'memory', 'cpu', 'disk', 'wifi_clients'} or not isinstance(items, list) or not items:
        return jsonify({'error': 'Parâmetros inválidos.'}), 400

    from sqlalchemy import func
    try:
        max_prio = db.session.query(func.max(MetricKeyProfile.priority)).filter(MetricKeyProfile.metric_type == metric_type).scalar() or 0
    except Exception:
        max_prio = 0
    next_prio = int(max_prio) + 1

    created = []
    skipped = []
    for it in items:
        key_string = (it.get('key_string') or '').strip()
        calc_str = (it.get('calculation_type') or '').strip().upper()
        if not key_string or calc_str not in {'DIRECT', 'INVERSE'}:
            skipped.append({'key_string': key_string, 'reason': 'dados inválidos'})
            continue

        exists = MetricKeyProfile.query.filter_by(metric_type=metric_type, key_string=key_string).all()
        if any((e.calculation_type.name if hasattr(e.calculation_type, 'name') else str(e.calculation_type)) == calc_str for e in exists):
            skipped.append({'key_string': key_string, 'reason': 'já existe'})
            continue

        prio = it.get('priority')
        try:
            prio = int(prio) if prio is not None else next_prio
        except Exception:
            prio = next_prio
        next_prio = max(next_prio, prio + 1)

        description = (it.get('description') or '').strip() or None
        is_active = bool(it.get('is_active', True))

        try:
            new_key = MetricKeyProfile(
                metric_type=metric_type,
                key_string=key_string,
                priority=prio,
                calculation_type=CalculationType[calc_str],
                description=description,
                is_active=is_active
            )
            db.session.add(new_key)
            created.append({'key_string': key_string, 'priority': prio})
        except Exception as e:
            current_app.logger.error(f"[{getattr(g, 'request_id', '-')}] Erro preparando cadastro em lote: {e}", exc_info=True)
            skipped.append({'key_string': key_string, 'reason': 'erro interno'})

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[{getattr(g, 'request_id', '-')}] Erro ao salvar cadastro em lote: {e}", exc_info=True)
        return jsonify({'error': 'Falha ao salvar no banco.'}), 500

    return jsonify({'created': created, 'skipped': skipped})
