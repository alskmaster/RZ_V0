# app/main/routes.py
import os
import json
import uuid
import threading
import traceback
import re
import datetime as dt
from flask import (render_template, redirect, url_for, send_file, 
                   send_from_directory, g, jsonify, request, flash, current_app)
from flask_login import login_required, current_user

from . import main
from app import db
from app.models import Client, Report, SystemConfig, User, ReportTemplate, MetricKeyProfile  # <-- adicionado MetricKeyProfile

# A importação foi dividida em duas para buscar cada função de seu arquivo de origem correto.
from app.services import (ReportGenerator, update_status, 
                          REPORT_GENERATION_TASKS, TASK_LOCK, AuditService)
from app.zabbix_api import obter_config_e_token_zabbix, fazer_request_zabbix


@main.before_app_request
def before_request_func():
    cfg = SystemConfig.query.first()
    if not cfg:
        # Cria um registro padrão para evitar falhas em templates que esperam g.sys_config
        try:
            cfg = SystemConfig()
            db.session.add(cfg)
            db.session.commit()
        except Exception:
            db.session.rollback()
    g.sys_config = cfg

def run_generation_in_thread(app_context, task_id, client_id, user_id, report_layout_json, date_from=None, date_to=None):
    with app_context:
        try:
            client = db.session.get(Client, int(client_id))
            author = db.session.get(User, user_id)
            system_config = SystemConfig.query.first()
            if not all([system_config, client, author]):
                update_status(task_id, "Erro: Dados inválidos.")
                return

            config_zabbix, erro_zabbix_config = obter_config_e_token_zabbix(current_app.config, task_id)
            if erro_zabbix_config:
                update_status(task_id, f"Erro: {erro_zabbix_config}")
                return

            generator = ReportGenerator(config_zabbix, task_id)
            pdf_path, error = generator.generate(client, None, system_config, author, report_layout_json, custom_start=date_from, custom_end=date_to)
            if error:
                update_status(task_id, f"Erro: {error}")
            else:
                with TASK_LOCK:
                    REPORT_GENERATION_TASKS[task_id]['file_path'] = pdf_path
                    REPORT_GENERATION_TASKS[task_id]['status'] = "Concluído"
        except Exception as e:
            error_trace = traceback.format_exc()
            current_app.logger.error(f"Erro fatal na thread (Task ID: {task_id}):\n{error_trace}")
            update_status(task_id, "Erro: Falha crítica durante a geração.")

# --- Rotas Principais do Usuário ---

@main.route('/')
@login_required
def index():
    return redirect(url_for('main.gerar_form'))
    
@main.route('/gerar')
@login_required
def gerar_form():
    clients = current_user.clients if current_user.has_role('client') else Client.query.order_by(Client.name).all()
    templates = ReportTemplate.query.order_by(ReportTemplate.name).all()
    return render_template('gerar_form.html', title="Gerar Relatório", clients=clients, templates=templates)

@main.route('/gerar_relatorio', methods=['POST'])
@login_required
def gerar_relatorio():
    task_id = str(uuid.uuid4())
    with TASK_LOCK:
        REPORT_GENERATION_TASKS[task_id] = {'status': 'Iniciando...'}
    
    client_id = request.form.get('client_id')
    date_from = request.form.get('date_from')
    date_to = request.form.get('date_to')
    report_layout_json = request.form.get('report_layout')

    # Migração automática de módulos legados para novos (Tabela/Gráficos)
    def _migrate_layout(layout):
        import copy, json
        try:
            mods = json.loads(layout) if isinstance(layout, str) else (layout or [])
        except Exception:
            return layout

        out = []
        for m in (mods or []):
            t = (m or {}).get('type')
            co = (m or {}).get('custom_options') or {}
            base = {k: v for k, v in m.items() if k != 'custom_options'}

            def _mk(new_type, title_suffix=None, extra_opts=None):
                nm = copy.deepcopy(base)
                nm['type'] = new_type
                nm['custom_options'] = {k: v for k, v in co.items()}
                for k in ('show_table', 'show_chart'):
                    nm['custom_options'].pop(k, None)
                if title_suffix:
                    nm['title'] = (nm.get('title') or '') + title_suffix
                if extra_opts:
                    nm['custom_options'].update(extra_opts)
                return nm

            if t == 'cpu':
                wants_table = co.get('show_table', True)
                wants_chart = co.get('show_chart', True)
                if wants_table:
                    out.append(_mk('cpu_table', ''))
                if wants_chart:
                    out.append(_mk('cpu_chart', ''))
            elif t == 'mem':
                wants_table = co.get('show_table', True)
                wants_chart = co.get('show_chart', True)
                if wants_table:
                    out.append(_mk('mem_table', ''))
                if wants_chart:
                    out.append(_mk('mem_chart', ''))
            elif t == 'latency':
                out.append(_mk('latency_table', ''))
                out.append(_mk('latency_chart', ''))
            elif t == 'loss':
                out.append(_mk('loss_table', ''))
                out.append(_mk('loss_chart', ''))
            elif t == 'sla':
                out.append(_mk('sla_table', ''))
            else:
                out.append(m)
        return out

    try:
        migrated = _migrate_layout(report_layout_json)
        import json as _json
        report_layout_json = _json.dumps(migrated)
    except Exception:
        pass
    thread = threading.Thread(target=run_generation_in_thread, args=(current_app.app_context(), task_id, client_id, current_user.id, report_layout_json, date_from, date_to))
    thread.daemon = True
    thread.start()
    return jsonify({'task_id': task_id})

@main.route('/report_status/<task_id>')
@login_required
def report_status(task_id):
    with TASK_LOCK:
        task = REPORT_GENERATION_TASKS.get(task_id, {'status': 'Tarefa não encontrada.'})
    return jsonify(task)

@main.route('/download_final_report/<task_id>')
@login_required
def download_final_report(task_id):
    with TASK_LOCK:
        task = REPORT_GENERATION_TASKS.get(task_id)
    
    if not task or 'file_path' not in task:
        flash("Arquivo do relatório não encontrado ou a tarefa expirou.", "danger")
        return redirect(url_for('main.gerar_form'))
    
    absolute_path = os.path.join(current_app.root_path, '..', task['file_path'])
    
    if os.path.exists(absolute_path):
        return send_file(absolute_path, as_attachment=True)
    else:
        current_app.logger.error(f"Tentativa de download falhou. Caminho não encontrado: {absolute_path}")
        flash("Arquivo do relatório não existe mais no servidor.", "danger")
        return redirect(url_for('main.gerar_form'))

@main.route('/history')
@login_required
def history():
    query = Report.query
    if current_user.has_role('client'):
        client_ids = [c.id for c in current_user.clients]
        query = query.filter(Report.client_id.in_(client_ids))
    reports = query.order_by(Report.created_at.desc()).all()
    return render_template('history.html', title="Histórico", reports=reports)

@main.route('/download_report/<int:report_id>')
@login_required
def download_report(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        flash("Relatório não encontrado.", "danger")
        return redirect(url_for('main.history'))
    is_authorized = not current_user.has_role('client') or report.client in current_user.clients
    if not is_authorized:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.history'))
        
    AuditService.log(f"Re-download do relatório '{report.filename}'")

    absolute_path = os.path.join(current_app.root_path, '..', report.file_path)

    if os.path.exists(absolute_path):
        return send_file(absolute_path, as_attachment=True)
    else:
        current_app.logger.error(f"Tentativa de download do histórico falhou. Caminho não encontrado: {absolute_path}")
        flash("Arquivo de relatório do histórico não encontrado no servidor.", "danger")
        return redirect(url_for('main.history'))

@main.route('/delete_report/<int:report_id>')
@login_required
def delete_report(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        flash("Relatório não encontrado.", "danger")
        return redirect(url_for('main.history'))

    is_authorized = not current_user.has_role('client') or report.author_id == current_user.id
    if not is_authorized:
        flash("Acesso negado. Você não tem permissão para excluir este relatório.", "danger")
        return redirect(url_for('main.history'))

    try:
        absolute_path = os.path.join(current_app.root_path, '..', report.file_path)
        
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
            current_app.logger.info(f"Arquivo '{report.file_path}' excluído com sucesso.")
        else:
            current_app.logger.warning(f"Tentativa de excluir arquivo que não existe: {absolute_path}")

        db.session.delete(report)
        db.session.commit()
        
        AuditService.log(f"Relatório '{report.filename}' excluído por {current_user.username}")
        flash(f"Relatório '{report.filename}' excluído com sucesso.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao tentar excluir o relatório {report.id}: {str(e)}")
        flash("Ocorreu um erro ao excluir o relatório.", "danger")
    
    return redirect(url_for('main.history'))

@main.route('/uploads/<path:filename>')
def uploaded_file(filename):
    upload_folder = os.path.join(current_app.root_path, '..', current_app.config['UPLOAD_FOLDER'])
    return send_from_directory(upload_folder, filename)

@main.route('/save_template', methods=['POST'])
@login_required
def save_template():
    data = request.json
    template_name = data.get('name')
    layout_json = data.get('layout')
    # migra antes de salvar
    def _migrate(layout):
        import json
        try:
            from copy import deepcopy
            mods = json.loads(layout) if isinstance(layout, str) else (layout or [])
        except Exception:
            return layout
        out = []
        for m in (mods or []):
            t = (m or {}).get('type')
            co = (m or {}).get('custom_options') or {}
            base = {k: v for k, v in m.items() if k != 'custom_options'}
            def mk(tp):
                mm = deepcopy(base); mm['type'] = tp; mm['custom_options'] = {k: v for k, v in co.items()};
                for k in ('show_table','show_chart'): mm['custom_options'].pop(k, None)
                return mm
            if t == 'cpu':
                if co.get('show_table', True): out.append(mk('cpu_table'))
                if co.get('show_chart', True): out.append(mk('cpu_chart'))
            elif t == 'mem':
                if co.get('show_table', True): out.append(mk('mem_table'))
                if co.get('show_chart', True): out.append(mk('mem_chart'))
            elif t == 'latency':
                out += [mk('latency_table'), mk('latency_chart')]
            elif t == 'loss':
                out += [mk('loss_table'), mk('loss_chart')]
            elif t == 'sla':
                out.append(mk('sla_table'))
            else:
                out.append(m)
        return json.dumps(out)

    try:
        layout_json = _migrate(layout_json)
    except Exception:
        pass
    
    if not template_name or not layout_json:
        return jsonify({'success': False, 'error': 'Nome do template e layout são obrigatórios.'}), 400

    existing_template = ReportTemplate.query.filter_by(name=template_name).first()
    if existing_template:
        return jsonify({'success': False, 'error': 'Já existe um template com este nome. Por favor, escolha outro.'}), 409
    
    try:
        new_template = ReportTemplate(name=template_name, layout_json=layout_json)
        db.session.add(new_template)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Template "{template_name}" salvo com sucesso!'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao salvar template: {e}")
        return jsonify({'success': False, 'error': 'Erro interno ao salvar o template.'}), 500

@main.route('/get_templates')
@login_required
def get_templates():
    templates = ReportTemplate.query.order_by(ReportTemplate.name).all()
    out = []
    for t in templates:
        lj = getattr(t, 'layout_json', None)
        # aplica migração apenas na visualização
        try:
            import json
            mods = json.loads(lj) if lj else []
            # troca simples dos tipos legados, sem duplicar
            mapping = {'cpu':'cpu_table','mem':'mem_table','latency':'latency_table','loss':'loss_table','sla':'sla_table'}
            for m in (mods or []):
                if m.get('type') in mapping:
                    m['type'] = mapping[m['type']]
            lj = json.dumps(mods)
        except Exception:
            pass
        out.append({'id': t.id, 'name': t.name, 'layout_json': lj})
    templates_list = out
    return jsonify(templates_list)


# --- Rotas de API para o Frontend ---

@main.route('/get_available_modules/<int:client_id>')
@login_required
def get_available_modules(client_id):
    client = db.session.get(Client, client_id)
    # relacionamento é lazy='dynamic' -> use count()/all()
    if not client or client.zabbix_groups.count() == 0:
        current_app.logger.debug(f"[get_available_modules] Cliente sem grupos (client_id={client_id})")
        return jsonify({'available_modules': []})

    # CORREÇÃO: atributo correto é 'group_id' e precisamos .all() para materializar
    group_ids = [g.group_id for g in client.zabbix_groups.all()]
    
    config_zabbix, erro = obter_config_e_token_zabbix(current_app.config)
    if erro:
        current_app.logger.error(f"Falha ao obter módulos para client_id {client_id}: {erro}")
        return jsonify({'error': f"Falha ao conectar ao Zabbix: {erro}", 'available_modules': []})

    body = {
        'jsonrpc': '2.0',
        'method': 'host.get',
        'params': {'groupids': group_ids, 'output': ['hostid']},
        'auth': config_zabbix['ZABBIX_TOKEN'],
        'id': 1
    }
    hosts = fazer_request_zabbix(body, config_zabbix['ZABBIX_URL'])
    
    if not isinstance(hosts, list) or not hosts:
        current_app.logger.debug(f"[get_available_modules] Nenhum host retornado para grupos {group_ids}")
        return jsonify({'available_modules': []})

    hostids = [h['hostid'] for h in hosts]
    
    def check_key(key):
        body_item = {
            'jsonrpc': '2.0',
            'method': 'item.get',
            'params': {'output': 'itemid', 'hostids': hostids, 'search': {'key_': key}, 'limit': 1},
            'auth': config_zabbix['ZABBIX_TOKEN'],
            'id': 1
        }
        items = fazer_request_zabbix(body_item, config_zabbix['ZABBIX_URL'])
        return isinstance(items, list) and len(items) > 0

    available_modules = []
    
    if check_key('icmpping'):        # Incidentes divididos
        available_modules.append({'type': 'incidents_table', 'name': 'Incidentes (Tabela)'})
        available_modules.append({'type': 'incidents_chart', 'name': 'Incidentes (Gráficos)'})
        available_modules.append({'type': 'unavailability_heatmap', 'name': 'Mapa de Calor de Indisponibilidade'})
        available_modules.append({'type': 'root_cause_top_triggers', 'name': 'Causa-Raiz (Top Gatilhos)'})
        available_modules.append({'type': 'mttr', 'name': 'Eficiência da Resposta (MTTR)'})
    
    if check_key('icmppingsec'):
        available_modules.append({'type': 'latency', 'name': 'Latência de Rede (Ping)'})
    if check_key('icmppingloss'):
        available_modules.append({'type': 'loss', 'name': 'Perda de Pacotes (Ping)'})

    if check_key('system.cpu.util'):
        available_modules.append({'type': 'cpu', 'name': 'Desempenho de CPU'})
        # CPU (novos módulos)
        available_modules.append({'type': 'cpu_table', 'name': 'CPU (Tabela)'})
        available_modules.append({'type': 'cpu_chart', 'name': 'CPU (Gráficos)'})
    if check_key('vm.memory.size[pused]') or check_key('vm.memory.size[pavailable]'):
        available_modules.append({'type': 'mem', 'name': 'Desempenho de Memória'})
    
    # Memória (novos módulos separados)
    try:
        if check_key('vm.memory.size[pused]') or check_key('vm.memory.size[pavailable]'):
            available_modules.append({'type': 'mem_table', 'name': 'Memória (Tabela)'})
            available_modules.append({'type': 'mem_chart', 'name': 'Memória (Gráficos)'})
    except Exception:
        pass

    # Ping (Latência e Perda) – novos módulos separados
    try:
        if check_key('icmppingsec'):
            available_modules.append({'type': 'latency_table', 'name': 'Latência (Tabela)'})
            available_modules.append({'type': 'latency_chart', 'name': 'Latência (Gráficos)'})
        if check_key('icmppingloss'):
            available_modules.append({'type': 'loss_table', 'name': 'Perda de Pacotes (Tabela)'})
            available_modules.append({'type': 'loss_chart', 'name': 'Perda de Pacotes (Gráficos)'})
    except Exception:
        pass

    if check_key('vfs.fs.size'):
        available_modules.append({'type': 'disk', 'name': 'Uso de Disco'})

    if check_key('net.if.in'):
        available_modules.append({'type': 'traffic_in', 'name': 'Tráfego de Entrada'})
        available_modules.append({'type': 'traffic_out', 'name': 'Tráfego de Saída'})
    
    # --------- NOVO: detecção de Wi-Fi (clientcountnumber / perfis wifi_clients) ----------
    try:
        wifi_keys = [p.key_string for p in MetricKeyProfile.query
                     .filter_by(metric_type='wifi_clients', is_active=True)
                     .order_by(MetricKeyProfile.priority.asc()).all()]
        if not wifi_keys:
            wifi_keys = ['clientcountnumber']  # fallback
    except Exception as e:
        current_app.logger.warning(f"[get_available_modules] Falha ao consultar MetricKeyProfile para Wi-Fi: {e}")
        wifi_keys = ['clientcountnumber']

    wifi_found = False
    for k in wifi_keys:
        if check_key(k):
            wifi_found = True
            break
    if wifi_found:
        available_modules.append({'type': 'wifi', 'name': 'Wi-Fi (Utilização por AP/SSID)'})
    # --------- FIM DO BLOCO NOVO ----------------------------------------------------------

    # Disponibilidade / SLA (novos)
    try:
        available_modules.append({'type': 'resilience_panel', 'name': 'Painel de Resiliência (SLA Preciso)'})
    except Exception:
        pass

    available_modules.append({'type': 'inventory', 'name': 'Inventário de Hosts'})
    available_modules.append({'type': 'html', 'name': 'Texto/HTML Customizado'})
    # Sempre disponivel: status do agente e MTTR
    available_modules.append({'type': 'agent_status', 'name': 'Status do Agente Zabbix'})
    # Novos módulos
    available_modules.append({'type': 'recurring_problems', 'name': 'Problemas Recorrentes'})
    available_modules.append({'type': 'critical_performance', 'name': 'Desempenho Crítico (por ItemID)'})
    
    # Limpa módulos legados do backend (mostrar apenas versões novas)
    # Extensoes adicionais
    available_modules.append({'type': 'capacity_forecast', 'name': 'Previsão de Capacidade'})
    available_modules.append({'type': 'itil_availability', 'name': 'Disponibilidade por Incidente (ITIL)'})
    available_modules.append({'type': 'executive_summary', 'name': 'Sumário Executivo'})
    legacy_types = {'cpu', 'mem', 'latency', 'loss', 'sla', 'sla_table', 'sla_chart', 'sla_plus', 'kpi', 'top_hosts', 'top_problems', 'stress', 'sla_incidents_table'}
    try:
        available_modules = [m for m in available_modules if m.get('type') not in legacy_types]
    except Exception:
        pass
    return jsonify({'available_modules': sorted(available_modules, key=lambda x: x['name'])})

@main.route('/get_client_interfaces/<int:client_id>')
@login_required
def get_client_interfaces(client_id):
    client = db.session.get(Client, client_id)
    # relacionamento é lazy='dynamic' -> use count()/all()
    if not client or client.zabbix_groups.count() == 0:
        current_app.logger.debug(f"[get_client_interfaces] Cliente sem grupos (client_id={client_id})")
    return jsonify({'interfaces': []})

@main.route('/search_items/<int:client_id>')
@login_required
def search_items(client_id):
    q = (request.args.get('q') or '').strip()
    limit = int(request.args.get('limit') or 20)
    client = db.session.get(Client, client_id)
    if not client or client.zabbix_groups.count() == 0 or not q:
        return jsonify({'items': []})

    group_ids = [g.group_id for g in client.zabbix_groups.all()]
    config_zabbix, erro = obter_config_e_token_zabbix(current_app.config)
    if erro:
        return jsonify({'items': [], 'error': erro})

    # hosts by group
    body_hosts = {
        'jsonrpc': '2.0', 'method': 'host.get',
        'params': {'groupids': group_ids, 'output': ['hostid','name']},
        'auth': config_zabbix['ZABBIX_TOKEN'], 'id': 1
    }
    hosts = fazer_request_zabbix(body_hosts, config_zabbix['ZABBIX_URL'])
    if not isinstance(hosts, list) or not hosts:
        return jsonify({'items': []})
    host_map = {str(h.get('hostid')): (h.get('name') or h.get('host') or str(h.get('hostid'))) for h in hosts}

    # items search by key_ substring
    body_items = {
        'jsonrpc': '2.0', 'method': 'item.get',
        'params': {
            'output': ['itemid','name','key_','hostid'],
            'hostids': [h['hostid'] for h in hosts],
            'search': {'key_': q},
            'limit': limit
        },
        'auth': config_zabbix['ZABBIX_TOKEN'], 'id': 1
    }
    items = fazer_request_zabbix(body_items, config_zabbix['ZABBIX_URL'])
    out = []
    if isinstance(items, list):
        for it in items:
            out.append({
                'itemid': str(it.get('itemid')),
                'name': it.get('name'),
                'key_': it.get('key_'),
                'host': host_map.get(str(it.get('hostid')), str(it.get('hostid')))
            })
    return jsonify({'items': out})

    # CORREÇÃO: atributo correto é 'group_id' e precisamos .all()
    group_ids = [g.group_id for g in client.zabbix_groups.all()]
    
    config_zabbix, erro = obter_config_e_token_zabbix(current_app.config)
    if erro:
        current_app.logger.warning(f'Falha ao conectar ao Zabbix ao listar interfaces para o cliente {client_id}: {erro}')
        return jsonify({'interfaces': []})

    body = {
        'jsonrpc': '2.0',
        'method': 'host.get',
        'params': {'groupids': group_ids, 'output': ['hostid']},
        'auth': config_zabbix['ZABBIX_TOKEN'],
        'id': 1
    }
    hosts = fazer_request_zabbix(body, config_zabbix['ZABBIX_URL'])
    
    if not isinstance(hosts, list) or not hosts:
        current_app.logger.debug(f"[get_client_interfaces] Nenhum host retornado para grupos {group_ids}")
        return jsonify({'interfaces': []})

    hostids = [h['hostid'] for h in hosts]
    
    body_item = {
        'jsonrpc': '2.0', 
        'method': 'item.get', 
        'params': {
            'output': ['key_'],
            'hostids': hostids, 
            'search': {'key_': 'net.if.in'}
        }, 
        'auth': config_zabbix['ZABBIX_TOKEN'], 
        'id': 1
    }
    items = fazer_request_zabbix(body_item, config_zabbix['ZABBIX_URL'])

    interfaces = set()
    if isinstance(items, list):
        for item in items:
            match = re.search(r'\[(.*?)\]', item['key_'])
            if match:
                interfaces.add(match.group(1))

    return jsonify({'interfaces': sorted(list(interfaces))})


# --- ROTA DE TESTE DE VALIDAÇÃO (TEMPORÁRIA) ---
@main.route('/test_events/<int:client_id>/<string:mes_ref>')
@login_required
def test_events(client_id, mes_ref):
    """
    Rota de diagnóstico para validar a coleta de eventos.
    Compara a coleta em lote (mês inteiro) com a coleta iterativa (dia a dia).
    """
    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"erro": "Cliente não encontrado"}), 404

    try:
        ref_date = dt.datetime.strptime(f'{mes_ref}-01', '%Y-%m-%d')
        start_date = ref_date.replace(day=1)
        end_date = (start_date.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    except ValueError:
        return jsonify({"erro": "Formato de data inválido. Use YYYY-MM"}), 400

    config_zabbix, erro = obter_config_e_token_zabbix(current_app.config)
    if erro:
        return jsonify({"erro": f"Falha ao conectar ao Zabbix: {erro}"}), 500

    # CORREÇÃO: 'group_id' + materialização com .all()
    group_ids = [g.group_id for g in client.zabbix_groups.all()]
    body_hosts = {'jsonrpc': '2.0', 'method': 'host.get', 'params': {'groupids': group_ids, 'output': ['hostid']}, 'auth': config_zabbix['ZABBIX_TOKEN'], 'id': 1}
    hosts = fazer_request_zabbix(body_hosts, config_zabbix['ZABBIX_URL'])
    if not isinstance(hosts, list) or not hosts:
        return jsonify({"erro": "Nenhum host encontrado para este cliente"}), 404
    all_host_ids = [h['hostid'] for h in hosts]

    # --- Coleta A: Método em Lote (Atual) ---
    periodo_lote = {
        'start': int(start_date.timestamp()),
        'end': int(end_date.replace(hour=23, minute=59, second=59).timestamp())
    }
    
    # Reutiliza a função de obter eventos do ReportGenerator
    from app.services import ReportGenerator
    generator_instance = ReportGenerator(config_zabbix, "test_task")
    
    eventos_lote = generator_instance.obter_eventos_wrapper(all_host_ids, periodo_lote, 'hostids')
    problemas_lote = [p for p in eventos_lote if p.get('source') == '0' and p.get('object') == '0' and p.get('value') == '1']
    total_lote = len(problemas_lote)

    # --- Coleta B: Método Dia a Dia ---
    total_diario = 0
    dias_com_eventos = {}
    current_day = start_date
    while current_day.month == start_date.month:
        dia_inicio = current_day.replace(hour=0, minute=0, second=0)
        dia_fim = current_day.replace(hour=23, minute=59, second=59)
        periodo_dia = {'start': int(dia_inicio.timestamp()), 'end': int(dia_fim.timestamp())}
        
        eventos_dia = generator_instance.obter_eventos_wrapper(all_host_ids, periodo_dia, 'hostids')
        problemas_dia = [p for p in eventos_dia if p.get('source') == '0' and p.get('object') == '0' and p.get('value') == '1']
        
        count_dia = len(problemas_dia)
        if count_dia > 0:
            dias_com_eventos[current_day.strftime('%Y-%m-%d')] = count_dia
        
        total_diario += count_dia
        current_day += dt.timedelta(days=1)

    # --- Resultados ---
    return jsonify({
        "cliente": client.name,
        "periodo_analisado": f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}",
        "contagem_metodo_em_lote": total_lote,
        "contagem_metodo_dia_a_dia": total_diario,
        "diferenca": total_diario - total_lote,
        "diagnostico": "Coleta em lote está INCOMPLETA." if total_diario > total_lote else "Coleta em lote parece COMPLETA.",
        "detalhes_diarios": dias_com_eventos
    })








