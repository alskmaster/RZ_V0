# app/services.py
import os
import json
import re
import datetime as dt
import threading
import traceback
import pandas as pd
from collections import defaultdict
from flask import render_template, current_app

from . import db
from .models import AuditLog, Report
from .zabbix_api import fazer_request_zabbix
from .pdf_builder import PDFBuilder

# ImportaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o dos nossos Plugins (Collectors)
from .collectors.cpu_collector import CpuCollector
from .collectors.mem_collector import MemCollector
from .collectors.disk_collector import DiskCollector
from .collectors.traffic_collector import TrafficCollector
from .collectors.latency_collector import LatencyCollector
from .collectors.loss_collector import LossCollector
from .collectors.inventory_collector import InventoryCollector
from .collectors.html_collector import HtmlCollector
from .collectors.sla_collector import SlaCollector
from .collectors.sla_plus_collector import SlaPlusCollector
from .collectors.sla_table_collector import SlaTableCollector
from .collectors.sla_chart_collector import SlaChartCollector
from .collectors.kpi_collector import KpiCollector
from .collectors.top_hosts_collector import TopHostsCollector
from .collectors.top_problems_collector import TopProblemsCollector
from .collectors.stress_collector import StressCollector
from .collectors.wifi_collector import WiFiCollector   # <-- NOVO

# --- Registro de Plugins ---
COLLECTOR_MAP = {
    'cpu': CpuCollector,
    'mem': MemCollector,
    'disk': DiskCollector,
    'traffic_in': TrafficCollector,
    'traffic_out': TrafficCollector,
    'latency': LatencyCollector,
    'loss': LossCollector,
    'inventory': InventoryCollector,
    'html': HtmlCollector,
    'kpi': KpiCollector,
    'sla': SlaCollector,
    'sla_plus': SlaPlusCollector,
    'sla_table': SlaTableCollector,
    'sla_chart': SlaChartCollector,
    'top_hosts': TopHostsCollector,
    'top_problems': TopProblemsCollector,
    'stress': StressCollector,
    'wifi': WiFiCollector,    # <-- NOVO
}

# --- Gerenciador de Tarefas e Auditoria ---
REPORT_GENERATION_TASKS = {}
TASK_LOCK = threading.Lock()

def update_status(task_id, message):
    with TASK_LOCK:
        if task_id in REPORT_GENERATION_TASKS:
            REPORT_GENERATION_TASKS[task_id]['status'] = message
    try:
        current_app.logger.info(f"TASK {task_id}: {message}")
    except Exception:
        pass


class AuditService:
    @staticmethod
    def log(action, user=None):
        from flask_login import current_user
        log_user = user or (current_user if current_user.is_authenticated else None)
        username = log_user.username if log_user else "Anonymous"
        user_id = log_user.id if log_user else None
        try:
            new_log = AuditLog(user_id=user_id, username=username, action=action)
            db.session.add(new_log)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Falha ao salvar log de auditoria: {e}")


class ReportGenerator:
    def __init__(self, config, task_id):
        self.config = config
        self.token = config.get('ZABBIX_TOKEN')
        self.url = config.get('ZABBIX_URL')
        self.task_id = task_id
        self.client = None
        self.system_config = None
        self.cached_data = {}
        if not self.token or not self.url:
            raise ValueError("ConfiguraÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o do Zabbix nÃƒÆ’Ã‚Â£o encontrada ou token invÃƒÆ’Ã‚Â¡lido.")

    def _update_status(self, message):
        update_status(self.task_id, message)

    # -------------------- SLA Helper (resiliente) --------------------
    def _get_client_sla_contract(self):
        """
        Tenta obter a meta de SLA do cliente de forma resiliente.
        - Procura por atributos comuns no objeto Client (futuro-compatÃƒÆ’Ã‚Â­vel).
        - Caso nÃƒÆ’Ã‚Â£o exista, tenta fallback em system_config (chave DEFAULT_SLA_CONTRACT se disponÃƒÆ’Ã‚Â­vel).
        - Se nada for encontrado, retorna None e loga aviso.
        """
        try:
            current_app.logger.debug(f"[ReportGenerator] Buscando SLA do cliente id={getattr(self.client, 'id', 'N/A')}")
            for attr in ("sla_contract", "sla", "sla_policy", "sla_plan", "sla_goal"):
                val = getattr(self.client, attr, None)
                if val is not None:
                    try:
                        fval = float(val)
                        current_app.logger.debug(f"[ReportGenerator] SLA encontrado em Client.{attr} = {fval}")
                        return fval
                    except Exception:
                        current_app.logger.debug(f"[ReportGenerator] SLA encontrado em Client.{attr} (nÃƒÆ’Ã‚Â£o numÃƒÆ’Ã‚Â©rico): {val}")
                        return val
        except Exception as e:
            current_app.logger.warning(f"[ReportGenerator] Falha ao inspecionar SLA no Client: {e}", exc_info=True)

        # Fallback: system_config pode ser objeto ORM ou dict
        fallback = None
        try:
            if isinstance(self.system_config, dict):
                fallback = self.system_config.get("DEFAULT_SLA_CONTRACT")
            else:
                fallback = getattr(self.system_config, "DEFAULT_SLA_CONTRACT", None)
        except Exception as e:
            current_app.logger.debug(f"[ReportGenerator] Erro ao consultar fallback de SLA em system_config: {e}")

        if fallback is not None:
            current_app.logger.debug(f"[ReportGenerator] Usando fallback DEFAULT_SLA_CONTRACT = {fallback}")
            try:
                return float(fallback)
            except Exception:
                return fallback

        current_app.logger.warning("[ReportGenerator] Nenhuma meta de SLA definida para o cliente; prosseguindo sem meta.")
        return None
    # ----------------------------------------------------------------

    def generate(self, client, ref_month_str, system_config, author, report_layout_json):
        """Gera o relatÃƒÆ’Ã‚Â³rio com base no layout configurado (JSON)."""
        self.client = client
        self.system_config = system_config
        self.cached_data = {}

        self._update_status("Iniciando geraÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o do relatÃƒÆ’Ã‚Â³rioÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")

        # --- PerÃƒÆ’Ã‚Â­odo de referÃƒÆ’Ã‚Âªncia ---
        try:
            ref_date = dt.datetime.strptime(f'{ref_month_str}-01', '%Y-%m-%d')
        except ValueError:
            return None, "Formato de mÃƒÆ’Ã‚Âªs de referÃƒÆ’Ã‚Âªncia invÃƒÆ’Ã‚Â¡lido. Use YYYY-MM."
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0)
        end_date = (start_date.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(seconds=1)
        period = {'start': int(start_date.timestamp()), 'end': int(end_date.timestamp())}
        current_app.logger.debug(f"[ReportGenerator.generate] perÃƒÆ’Ã‚Â­odo={period} ref={ref_month_str}")

        # --- Grupos do cliente (RELACIONAMENTO DINÃƒÆ’Ã¢â‚¬Å¡MICO) ---
        try:
            groups_rel = client.zabbix_groups.all() if hasattr(client.zabbix_groups, "all") else client.zabbix_groups
            group_ids = [g.group_id for g in groups_rel if getattr(g, "group_id", None)]
        except Exception as e:
            current_app.logger.error(f"[ReportGenerator.generate] Falha ao obter grupos do cliente {client.id}: {e}", exc_info=True)
            group_ids = []

        current_app.logger.debug(f"[ReportGenerator.generate] client_id={client.id} group_ids={group_ids}")

        if not group_ids:
            return None, f"O cliente '{client.name}' nÃƒÆ’Ã‚Â£o possui Grupos Zabbix associados."

        # --- Hosts do cliente ---
        self._update_status("Coletando hosts do cliente...")
        all_hosts = self.get_hosts(group_ids)
        if not all_hosts:
            return None, f"Nenhum host encontrado para os grupos Zabbix do cliente {client.name}."
        self.cached_data['all_hosts'] = all_hosts
        current_app.logger.debug(f"[ReportGenerator.generate] hosts_carregados={len(all_hosts)}")

        # --- Layout solicitado ---
        try:
            report_layout = json.loads(report_layout_json) if isinstance(report_layout_json, str) else report_layout_json
        except Exception as e:
            current_app.logger.error(f"[ReportGenerator.generate] Layout JSON invÃƒÆ’Ã‚Â¡lido: {e}", exc_info=True)
            return None, "Layout invÃƒÆ’Ã‚Â¡lido (JSON)."

        availability_data_cache = None
        sla_prev_month_df = None

        availability_module_types = {'sla', 'sla_table', 'sla_chart', 'sla_plus', 'kpi', 'top_hosts', 'top_problems', 'stress'}

        final_html_parts = []

        # PrÃƒÆ’Ã‚Â©-coleta de disponibilidade (SLA/KPI/Top)
        if any(mod.get('type') in availability_module_types for mod in (report_layout or [])):
            self._update_status("Coletando dados de Disponibilidade (SLA)ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")
            sla_contract = self._get_client_sla_contract()
            try:
                availability_data_cache, error_msg = self._collect_availability_data(all_hosts, period, sla_contract)
            except Exception as e:
                current_app.logger.error(f"[ReportGenerator.generate] Excecao na pre-coleta de SLA: {e}", exc_info=True)
                final_html_parts.append("<p>Erro critico ao coletar dados de disponibilidade (falha inesperada).</p>")
                availability_data_cache = {}
                error_msg = "Falha inesperada na pre-coleta de SLA"
            if error_msg:
                current_app.logger.warning(f"[ReportGenerator.generate] Erro SLA primÃƒÆ’Ã‚Â¡rio: {error_msg}")
                final_html_parts.append(f"<p>Erro crÃƒÆ’Ã‚Â­tico ao coletar dados de disponibilidade: {error_msg}</p>")
                availability_data_cache = {}

        # MÃƒÆ’Ã‚Âªs anterior para SLA comparativo
        sla_module_config = next((mod for mod in (report_layout or []) if mod.get('type') == 'sla'), None)
        if sla_module_config and availability_data_cache:
            custom_options = sla_module_config.get('custom_options', {})
            if custom_options.get('compare_to_previous_month'):
                self._update_status("Coletando dados do mÃƒÆ’Ã‚Âªs anterior para comparaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o de SLAÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")
                prev_ref_date = ref_date - dt.timedelta(days=1)
                prev_month_start = prev_ref_date.replace(day=1)
                prev_month_end = (prev_month_start.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(seconds=1)
                prev_period = {'start': int(prev_month_start.timestamp()), 'end': int(prev_month_end.timestamp())}

                sla_contract = self._get_client_sla_contract()
                try:
                    prev_data, prev_error = self._collect_availability_data(all_hosts, prev_period, sla_contract, trends_only=True)
                except Exception as e:
                    current_app.logger.error(f"[ReportGenerator.generate] Excecao na coleta do mes anterior (SLA): {e}", exc_info=True)
                    prev_data, prev_error = None, "Falha inesperada na coleta do mes anterior"
                if prev_error:
                    self._update_status(f"Aviso: Falha ao coletar dados do mÃƒÆ’Ã‚Âªs anterior: {prev_error}")
                elif prev_data and 'df_sla_problems' in prev_data:
                    sla_prev_month_df = prev_data['df_sla_problems'].rename(columns={'SLA (%)': 'SLA_anterior'})
                    self.cached_data['prev_month_sla_df'] = prev_data['df_sla_problems']

        # Montagem dos mÃƒÆ’Ã‚Â³dulos
        for module_config in (report_layout or []):
            module_type = module_config.get('type')
            collector_class = COLLECTOR_MAP.get(module_type)
            if not collector_class:
                self._update_status(f"Aviso: Nenhum plugin encontrado para o tipo '{module_type}'.")
                continue

            try:
                collector_instance = collector_class(self, module_config)
                html_part = ""
                if module_type in availability_module_types:
                    if availability_data_cache:
                        if module_type in {'sla', 'sla_table', 'sla_chart', 'sla_plus'}:
                            html_part = collector_instance.collect(all_hosts, period, availability_data_cache, df_prev_month=sla_prev_month_df)
                        else:
                            html_part = collector_instance.collect(all_hosts, period, availability_data_cache)
                    else:
                        html_part = "<p>Dados de disponibilidade indisponíveis para este módulo.</p>"
                else:
                    html_part = collector_instance.collect(all_hosts, period):
                            html_part = collector_instance.collect(all_hosts, period, availability_data_cache)
                    else:
                        html_part = "<p>Dados de disponibilidade indisponÃƒÆ’Ã‚Â­veis para este mÃƒÆ’Ã‚Â³dulo.</p>"
                else:
                    html_part = collector_instance.collect(all_hosts, period)

                final_html_parts.append(html_part)
            except Exception as e:
                current_app.logger.error(f"Erro ao executar o plugin '{module_type}': {e}", exc_info=True)
                final_html_parts.append(f"<p>Erro crÃƒÆ’Ã‚Â­tico ao processar mÃƒÆ’Ã‚Â³dulo '{module_type}'.</p>")

        # Miolo + PDF
        dados_gerais = {
            'group_name': client.name,
            'periodo_referencia': start_date.strftime('%B de %Y').capitalize(),
            'data_emissao': dt.datetime.now().strftime('%d/%m/%Y'),
            'report_content': "".join(final_html_parts)
        }
        try:
            miolo_html = render_template('_MIOLO_BASE.html', **dados_gerais, modules={'pandas': pd})
        except Exception as e:
            current_app.logger.error(f"[ReportGenerator.generate] Falha ao renderizar miolo HTML: {e}", exc_info=True)
            return None, "Falha ao renderizar o conteudo do relatorio."

        self._update_status("Montando o relatÃƒÆ’Ã‚Â³rio finalÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")

        try:
            pdf_builder = PDFBuilder(self.task_id)
            error = pdf_builder.add_cover_page(system_config.report_cover_path)
            if error:
                return None, error
            error = pdf_builder.add_miolo_from_html(miolo_html)
            if error:
                return None, error
            error = pdf_builder.add_final_page(system_config.report_final_page_path)
            if error:
                return None, error
        except Exception as e:
            current_app.logger.error(f"[ReportGenerator.generate] Excecao durante a montagem do PDF: {e}", exc_info=True)
            return None, "Falha ao montar o PDF do relatorio."

        pdf_filename = f'Relatorio_Custom_{client.name.replace(" ", "_")}_{ref_month_str}_{os.urandom(4).hex()}.pdf'
        pdf_path = os.path.join(current_app.config['GENERATED_REPORTS_FOLDER'], pdf_filename)

        final_file_path = pdf_builder.save_and_cleanup(pdf_path)

        report_record = Report(
            filename=pdf_filename,
            file_path=pdf_path,
            reference_month=ref_month_str,
            user_id=author.id,
            client_id=client.id,
            report_type='custom'
        )
        db.session.add(report_record)
        db.session.commit()
        AuditService.log(f"Gerou relatÃƒÆ’Ã‚Â³rio customizado para '{client.name}' referente a {ref_month_str}", user=author)
        return pdf_path, None

    # -------------------- Bloco de coleta / utilidades --------------------

    def _collect_availability_data(self, all_hosts, period, sla_goal, trends_only=False):
        if sla_goal is None:
            current_app.logger.debug("[Availability] Nenhuma meta de SLA definida; calculando disponibilidade sem metas.")

        all_host_ids = [h['hostid'] for h in all_hosts]

        # Itens de PING com triggers (necessÃƒÆ’Ã‚Â¡rios para correlacionar eventos de indisponibilidade)
        ping_items = self.get_items(all_host_ids, 'icmpping', search_by_key=True, include_triggers=True)
        if not ping_items:
            return None, "Nenhum item de monitoramento de PING ('icmpping') encontrado."

        hosts_with_ping_ids = {item['hostid'] for item in ping_items}
        hosts_for_sla = [host for host in all_hosts if host['hostid'] in hosts_with_ping_ids]
        if not hosts_for_sla:
            return None, "Nenhum dos hosts neste grupo tem um item de PING para calcular o SLA."

        ping_trigger_ids = list({t['triggerid'] for item in ping_items for t in (item.get('triggers') or [])})
        if not ping_trigger_ids:
            return None, "Nenhum gatilho (trigger) de PING encontrado para os itens deste grupo."

        ping_events = self.obter_eventos_wrapper(ping_trigger_ids, period, 'objectids')
        if ping_events is None:
            return None, "Falha na coleta de eventos de PING."

        ping_problems = [p for p in ping_events if p.get('source') == '0' and p.get('object') == '0' and p.get('value') == '1']
        correlated_ping_problems = self._correlate_problems(ping_problems, ping_events, period)
        df_sla = pd.DataFrame(self._calculate_sla(correlated_ping_problems, hosts_for_sla, period))
        try:
            for _c in list(df_sla.columns):
                if ('Tempo' in str(_c)) and ('Indispon' in str(_c)) and _c != 'Tempo IndisponÃƒÂ­vel':
                    df_sla.rename(columns={_c: 'Tempo IndisponÃƒÂ­vel'}, inplace=True)
        except Exception:
            pass

        if trends_only:
            return {'df_sla_problems': df_sla}, None

        all_group_events = self.obter_eventos_wrapper(all_host_ids, period, 'hostids')
        if all_group_events is None:
            return None, "Falha na coleta de eventos gerais do grupo."

        all_problems = [p for p in all_group_events if p.get('source') == '0' and p.get('object') == '0' and p.get('value') == '1']
        df_top_incidents = self._count_problems_by_host(all_problems, all_hosts)
        # Compatibilidade com coletores: garante colunas 'Problema' e 'OcorrÃƒÂªncias'
        try:
            import pandas as _pd
            if isinstance(df_top_incidents, _pd.DataFrame):
                if 'Problemas' in df_top_incidents.columns and 'OcorrÃƒÂªncias' not in df_top_incidents.columns:
                    df_top_incidents = df_top_incidents.rename(columns={'Problemas': 'OcorrÃƒÂªncias'})
                if 'Problema' not in df_top_incidents.columns and 'OcorrÃƒÂªncias' in df_top_incidents.columns:
                    df_top_incidents['Problema'] = 'Indisponibilidade'
        except Exception:
            pass

        avg_sla = df_sla['SLA (%)'].mean() if not df_sla.empty else 100.0
        principal_ofensor = df_top_incidents.iloc[0]['Host'] if not df_top_incidents.empty else "Nenhum"

        self._update_status("Calculando tendÃƒÆ’Ã‚Âªncias de KPIsÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")
        ref_date = dt.datetime.fromtimestamp(period['start'])
        prev_ref_date = ref_date - dt.timedelta(days=1)
        prev_month_start = prev_ref_date.replace(day=1)
        prev_month_end = (prev_month_start.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(seconds=1)
        prev_period = {'start': int(prev_month_start.timestamp()), 'end': int(prev_month_end.timestamp())}

        prev_ping_events = self.obter_eventos_wrapper(ping_trigger_ids, prev_period, 'objectids')
        prev_avg_sla = 100.0
        if prev_ping_events:
            prev_ping_problems = [p for p in prev_ping_events if p.get('source') == '0' and p.get('object') == '0' and p.get('value') == '1']
            prev_correlated = self._correlate_problems(prev_ping_problems, prev_ping_events, prev_period)
            prev_df_sla = pd.DataFrame(self._calculate_sla(prev_correlated, hosts_for_sla, prev_period))
            if not prev_df_sla.empty:
                prev_avg_sla = prev_df_sla['SLA (%)'].mean()

        prev_all_group_events = self.obter_eventos_wrapper(all_host_ids, prev_period, 'hostids')
        prev_all_problems_count = 0
        if prev_all_group_events:
            prev_all_problems_count = len([p for p in prev_all_group_events if p.get('source') == '0' and p.get('object') == '0' and p.get('value') == '1'])

        sla_trend = 'stable'
        if avg_sla > prev_avg_sla:
            sla_trend = 'up'
        elif avg_sla < prev_avg_sla:
            sla_trend = 'down'

        incidents_trend = 'stable'
        if len(all_problems) < prev_all_problems_count:
            incidents_trend = 'up'
        elif len(all_problems) > prev_all_problems_count:
            incidents_trend = 'down'

        kpis_data = {
            'avg_sla': avg_sla,
            'prev_avg_sla': prev_avg_sla,
            'sla_trend': sla_trend,
            'principal_ofensor': principal_ofensor,
            'incidents_count': len(all_problems),
            'incidents_trend': incidents_trend
        }

        from collections import defaultdict
        severity_map = {'0': 'Not classified', '1': 'Information', '2': 'Warning', '3': 'Average', '4': 'High', '5': 'Disaster'}
        severity_counts = defaultdict(int)
        for problem in all_problems:
            level = problem.get('severity', '0')
            severity_counts[severity_map.get(level, 'Unknown')] += 1

        return {
            'kpis': kpis_data,
            'df_sla_problems': df_sla,
            'df_top_incidents': df_top_incidents,
            'severity_counts': dict(severity_counts)
        }, None

    def _normalize_string(self, s):
        return re.sub(r'\s+', ' ', str(s).replace('\n', ' ').replace('\r', ' ')).strip()

    def get_hosts(self, groupids):
        """Coleta hosts de um ou mais grupos com IP e nomes normalizados."""
        self._update_status("Coletando dados de hostsÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")
        body = {
            'jsonrpc': '2.0',
            'method': 'host.get',
            'params': {
                'groupids': groupids,
                'selectInterfaces': ['ip'],
                'output': ['hostid', 'host', 'name']
            },
            'auth': self.token,
            'id': 1
        }
        resposta = fazer_request_zabbix(body, self.url)
        if not isinstance(resposta, list):
            return []
        return sorted([
            {
                'hostid': item.get('hostid'),
                'hostname': item.get('host'),
                'nome_visivel': self._normalize_string(item.get('name', '')),
                'ip0': (item.get('interfaces') or [{}])[0].get('ip', 'N/A')
            }
            for item in resposta
        ], key=lambda x: x['nome_visivel'])

    def shared_collect_latency_and_loss(self, all_hosts, period):
        host_ids = [h['hostid'] for h in all_hosts]
        host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}

        lat_items = self.get_items(host_ids, 'icmppingsec', search_by_key=True)
        df_lat = pd.DataFrame()
        if lat_items:
            lat_trends = self.get_trends([item['itemid'] for item in lat_items], period['start'], period['end'])
            df_lat = self._process_trends(lat_trends, lat_items, host_map, unit_conversion_factor=1000)

        loss_items = self.get_items(host_ids, 'icmppingloss', search_by_key=True)
        df_loss = pd.DataFrame()
        if loss_items:
            loss_trends = self.get_trends([item['itemid'] for item in loss_items], period['start'], period['end'])
            df_loss = self._process_trends(loss_trends, loss_items, host_map)

        if df_lat.empty and df_loss.empty:
            return None, "Nenhum item de LatÃƒÆ’Ã‚Âªncia ('icmppingsec') ou Perda ('icmppingloss') encontrado."

        return {'df_lat': df_lat, 'df_loss': df_loss}, None






    # -------------------- Itens e SÃƒÆ’Ã‚Â©ries (Trends/History) --------------------
    def get_items(self, hostids, filter_key, search_by_key=False, exact_key_search=False, include_triggers=False):
        """Busca itens do Zabbix por hosts, filtrando por key ou name.
        - search_by_key: usa 'search' em key_ (substring) ou 'filter' (exato) se exact_key_search=True
        - include_triggers: inclui 'selectTriggers' = 'extend'
        Retorna lista (possivelmente vazia).
        """
        self._update_status(f"Buscando itens com filtro '{filter_key}'ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")
        params = {
            'output': ['itemid', 'hostid', 'name', 'key_', 'value_type'],
            'hostids': hostids,
            'sortfield': 'name'
        }
        if search_by_key:
            if exact_key_search:
                params['filter'] = {'key_': filter_key if isinstance(filter_key, list) else [filter_key]}
            else:
                params['search'] = {'key_': filter_key if isinstance(filter_key, str) else (filter_key[0] if filter_key else '')}
        else:
            params['search'] = {'name': filter_key}
        if include_triggers:
            params['selectTriggers'] = 'extend'
        body = {
            'jsonrpc': '2.0',
            'method': 'item.get',
            'params': params,
            'auth': self.token,
            'id': 1
        }
        return fazer_request_zabbix(body, self.url) or []

    def get_trends(self, itemids, time_from=None, time_till=None):
        if isinstance(time_from, dict) and time_till is None:
            period = time_from
            time_from = int(period.get('start'))
            time_till = int(period.get('end'))
            current_app.logger.debug("[ReportGenerator.get_trends] Back-compat: recebido dict 'period'.")
        if time_from is None or time_till is None:
            raise TypeError("get_trends() requer time_from e time_till, ou um dict 'period' como 2Ãƒâ€šÃ‚Âº argumento.")
        self._update_status(f"Buscando tendÃƒÆ’Ã‚Âªncias para {len(itemids)} itensÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")
        body = {
            'jsonrpc': '2.0',
            'method': 'trend.get',
            'params': {
                'output': ['itemid', 'clock', 'num', 'value_min', 'value_avg', 'value_max'],
                'itemids': itemids,
                'time_from': int(time_from),
                'time_till': int(time_till)
            },
            'auth': self.token,
            'id': 1
        }
        trends = fazer_request_zabbix(body, self.url)
        if not isinstance(trends, list):
            current_app.logger.error(f"Falha ao buscar trends para {len(itemids)} itens. Resposta invÃƒÆ’Ã‚Â¡lida do Zabbix.")
            return []
        return trends

    def _iter_chunks(self, seq, size):
        for i in range(0, len(seq), size):
            yield seq[i:i+size]

    def _aggregate_trends(self, itemids, time_from, time_till, chunk_size=200):
        all_rows = []
        for chunk in self._iter_chunks(itemids, chunk_size):
            body = {
                'jsonrpc': '2.0',
                'method': 'trend.get',
                'params': {
                    'output': ['itemid', 'clock', 'num', 'value_min', 'value_avg', 'value_max'],
                    'itemids': chunk,
                    'time_from': int(time_from),
                    'time_till': int(time_till)
                },
                'auth': self.token,
                'id': 1
            }
            rows = fazer_request_zabbix(body, self.url)
            if isinstance(rows, list):
                all_rows.extend(rows)
        return all_rows

    def get_history_aggregate(self, itemids, time_from, time_till, history_value_type=0, chunk_size=200):
        import pandas as pd
        all_rows = []
        ids = [str(i) for i in itemids]
        for chunk in self._iter_chunks(ids, chunk_size):
            body = {
                'jsonrpc': '2.0',
                'method': 'history.get',
                'params': {
                    'output': ['itemid', 'clock', 'value'],
                    'history': int(history_value_type),
                    'itemids': chunk,
                    'time_from': int(time_from),
                    'time_till': int(time_till)
                },
                'auth': self.token,
                'id': 1
            }
            rows = fazer_request_zabbix(body, self.url)
            if isinstance(rows, list):
                all_rows.extend(rows)
        if not all_rows:
            return []
        df = pd.DataFrame(all_rows)
        df['itemid'] = df['itemid'].astype(str)
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        agg = df.groupby('itemid')['value'].agg(value_min='min', value_avg='mean', value_max='max').reset_index()
        return agg.to_dict(orient='records')

    def robust_aggregate(self, itemids, time_from, time_till, items_meta=None):
        rows = self._aggregate_trends(itemids, time_from, time_till)
        if isinstance(rows, list) and len(rows) > 0:
            return rows
        groups = {0: [], 3: []}
        if items_meta:
            for it in items_meta:
                iid = str(it.get('itemid'))
                try:
                    vt = int(it.get('value_type'))
                except Exception:
                    vt = 0
                if vt in (0, 3):
                    groups[vt].append(iid)
                else:
                    groups[0].append(iid)
        else:
            groups[0] = [str(i) for i in itemids]
        combined = []
        for vt, ids in groups.items():
            if not ids:
                continue
            combined.extend(self.get_history_aggregate(ids, time_from, time_till, history_value_type=vt))
        return combined

    def get_history_points(self, itemids, time_from, time_till, history_value_type=0, chunk_size=200):
        all_rows = []
        ids = [str(i) for i in itemids]
        for chunk in self._iter_chunks(ids, chunk_size):
            body = {
                'jsonrpc': '2.0',
                'method': 'history.get',
                'params': {
                    'output': ['itemid', 'clock', 'value'],
                    'history': int(history_value_type),
                    'itemids': chunk,
                    'time_from': int(time_from),
                    'time_till': int(time_till)
                },
                'auth': self.token,
                'id': 1
            }
            rows = fazer_request_zabbix(body, self.url)
            if isinstance(rows, list):
                all_rows.extend(rows)
        return all_rows

    def _process_trends(self, trends, items, host_map, unit_conversion_factor=1, is_pavailable=False, agg_method='mean'):
        import pandas as pd
        if not isinstance(trends, list) or not trends:
            return pd.DataFrame(columns=['Host', 'Min', 'Max', 'Avg'])
        df = pd.DataFrame(trends)
        df[['value_min', 'value_avg', 'value_max']] = df[['value_min', 'value_avg', 'value_max']].astype(float)
        item_to_host_map = {str(item['itemid']): item['hostid'] for item in items}
        df['itemid'] = df['itemid'].astype(str)
        df['hostid'] = df['itemid'].map(item_to_host_map)
        agg_functions = {'Min': ('value_min', agg_method), 'Max': ('value_max', agg_method), 'Avg': ('value_avg', agg_method)}
        agg_results = df.groupby('hostid').agg(**agg_functions).reset_index()
        if is_pavailable:
            agg_results['Min_old'], agg_results['Max_old'] = agg_results['Min'], agg_results['Max']
            agg_results['Min'], agg_results['Max'] = 100 - agg_results['Max_old'], 100 - agg_results['Min_old']
            agg_results['Avg'] = 100 - agg_results['Avg']
            agg_results.drop(columns=['Min_old', 'Max_old'], inplace=True)
        for col in ['Min', 'Max', 'Avg']:
            agg_results[col] *= unit_conversion_factor
        agg_results['Host'] = agg_results['hostid'].map(host_map)
        return agg_results[['Host', 'Min', 'Max', 'Avg']]

    def obter_eventos(self, object_ids, periodo, id_type='hostids', max_depth=3):
        time_from, time_till = periodo['start'], periodo['end']
        if max_depth <= 0:
            current_app.logger.error("ERRO: Limite de profundidade de recursÃƒÆ’Ã‚Â£o atingido para obter eventos.")
            return None
        params = {
            'output': 'extend', 'selectHosts': ['hostid'], 'time_from': time_from, 'time_till': time_till,
            id_type: object_ids, 'sortfield': ["eventid"], 'sortorder': "ASC", 'select_acknowledges': 'extend'
        }
        body = {'jsonrpc': '2.0', 'method': 'event.get', 'params': params, 'auth': self.token, 'id': 1}
        resposta = fazer_request_zabbix(body, self.url, allow_retry=False)
        if isinstance(resposta, dict) and 'error' in resposta:
            self._update_status("Consulta pesada detectada, quebrando o perÃƒÆ’Ã‚Â­odoÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")
            mid_point = time_from + (time_till - time_from) // 2
            periodo1 = {'start': time_from, 'end': mid_point}
            periodo2 = {'start': mid_point + 1, 'end': time_till}
            eventos1 = self.obter_eventos(object_ids, periodo1, id_type, max_depth - 1)
            if eventos1 is None:
                return None
            eventos2 = self.obter_eventos(object_ids, periodo2, id_type, max_depth - 1)
            if eventos2 is None:
                return None
            return eventos1 + eventos2
        return resposta

    def obter_eventos_wrapper(self, object_ids, periodo, id_type='objectids'):
        if not object_ids:
            return []
        self._update_status(f"Processando eventos para {len(object_ids)} objetos em uma ÃƒÆ’Ã‚Âºnica chamadaÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦")
        all_events = self.obter_eventos(object_ids, periodo, id_type)
        if all_events is None:
            current_app.logger.critical("Falha crÃƒÆ’Ã‚Â­tica ao coletar eventos para os IDs. Abortando.")
            return None
        return sorted(all_events, key=lambda x: int(x['clock']))

    # -------------------- Helpers de SLA (correlaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o e agregaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Âµes) --------------------
    def _correlate_problems(self, problems, all_events, period=None):
        """
        Pareia eventos de problema (value='1') com o primeiro evento subsequente de recuperaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o (value='0')
        do mesmo trigger (objectid). Se nÃƒÆ’Ã‚Â£o houver recuperaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o, encerra no fim do perÃƒÆ’Ã‚Â­odo consultado.
        Retorna lista de dicts com: triggerid, hostid, start, end.
        """
        if not problems:
            return []
        events_by_trigger = {}
        for ev in (all_events or []):
            tid = ev.get('objectid') or ev.get('triggerid')
            if tid is None:
                continue
            key = str(tid)
            events_by_trigger.setdefault(key, []).append(ev)
        for evs in events_by_trigger.values():
            try:
                evs.sort(key=lambda e: int(e.get('clock', 0)))
            except Exception:
                pass

        correlated = []
        for p in problems:
            try:
                tid = str(p.get('objectid') or p.get('triggerid'))
                if not tid:
                    continue
                evs = events_by_trigger.get(tid, [])
                p_clock = int(p.get('clock'))
                hostid = None
                hosts = p.get('hosts') or []
                if hosts and isinstance(hosts, list):
                    hostid = (hosts[0] or {}).get('hostid')
                end_clock = None
                for ev in evs:
                    if int(ev.get('clock', 0)) > p_clock and str(ev.get('value', '0')) == '0':
                        end_clock = int(ev['clock'])
                        break
                if end_clock is None:
                    # Se nÃƒÆ’Ã‚Â£o tiver recuperaÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o, usa o fim do perÃƒÆ’Ã‚Â­odo (se fornecido) ou o ÃƒÆ’Ã‚Âºltimo evento
                    if period and 'end' in period:
                        try:
                            end_clock = int(period['end'])
                        except Exception:
                            end_clock = None
                if end_clock is None and evs:
                    end_clock = int(evs[-1].get('clock', p_clock))
                if end_clock is None:
                    end_clock = p_clock
                correlated.append({
                    'triggerid': tid,
                    'hostid': hostid,
                    'start': p_clock,
                    'end': end_clock if end_clock >= p_clock else p_clock
                })
            except Exception:
                continue
        return correlated

    def _calculate_sla(self, correlated_problems, hosts_for_sla, period):
        """
        Calcula SLA por host a partir de janelas de indisponibilidade correlacionadas.
        Retorna lista de dicts com Host, SLA (%) e Tempo IndisponÃƒÆ’Ã‚Â­vel (horas).
        """
        if not hosts_for_sla:
            return []
        host_map = {str(h['hostid']): h['nome_visivel'] for h in hosts_for_sla}
        p_start = int(period.get('start', 0))
        p_end = int(period.get('end', 0))
        period_seconds = max(1, p_end - p_start + 1)
        downtime_by_host = {hid: 0 for hid in host_map.keys()}

        for pr in (correlated_problems or []):
            hid = pr.get('hostid')
            if hid is None:
                continue
            hid = str(hid)
            if hid not in downtime_by_host:
                continue
            s = max(p_start, int(pr.get('start', p_start)))
            e = min(p_end, int(pr.get('end', p_end)))
            if e > s:
                downtime_by_host[hid] += (e - s)

        rows = []
        for hid, down in downtime_by_host.items():
            sla = max(0.0, min(100.0, 100.0 * (1.0 - (down / period_seconds))))
            rows.append({
                'Host': host_map.get(hid, f'Host {hid}'),
                'SLA (%)': float(sla),
                'Tempo IndisponÃƒÆ’Ã‚Â­vel': round(down / 3600.0, 2)
            })
        return rows

    def _count_problems_by_host(self, problems, all_hosts):
        """
        Conta eventos de problema por host e retorna DataFrame (ou lista compatÃƒÆ’Ã‚Â­vel) ordenado.
        """
        import pandas as pd
        from collections import Counter
        host_map = {str(h['hostid']): h['nome_visivel'] for h in (all_hosts or [])}
        counter = Counter()
        for p in (problems or []):
            hosts = p.get('hosts') or []
            hid = None
            if hosts:
                hid = str((hosts[0] or {}).get('hostid'))
            if hid:
                counter[hid] += 1
        rows = [{'Host': host_map.get(hid, f'Host {hid}'), 'Problemas': count}
                for hid, count in counter.most_common()]
        return pd.DataFrame(rows)

