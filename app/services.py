"""
Clean services.py (ASCII only)
Consolidates the prior working logic with new modules (sla_chart, sla_table, sla_plus).
"""

import os
import json
import re
import datetime as dt
import threading
import traceback
from collections import defaultdict

import pandas as pd
from flask import render_template, current_app

from . import db
from .models import AuditLog, Report
from .zabbix_api import fazer_request_zabbix
from .pdf_builder import PDFBuilder

# Collectors
from .collectors.cpu_collector import CpuCollector
from .collectors.mem_collector import MemCollector
from .collectors.disk_collector import DiskCollector
from .collectors.traffic_collector import TrafficCollector
from .collectors.latency_collector import LatencyCollector
from .collectors.loss_collector import LossCollector
from .collectors.inventory_collector import InventoryCollector
from .collectors.html_collector import HtmlCollector
from .collectors.sla_collector import SlaCollector
from .collectors.sla_table_collector import SlaTableCollector
from .collectors.sla_chart_collector import SlaChartCollector
from .collectors.sla_plus_collector import SlaPlusCollector
from .collectors.kpi_collector import KpiCollector
from .collectors.top_hosts_collector import TopHostsCollector
from .collectors.top_problems_collector import TopProblemsCollector
from .collectors.stress_collector import StressCollector
from .collectors.wifi_collector import WiFiCollector


# Registry of collectors
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
    'sla_table': SlaTableCollector,
    'sla_chart': SlaChartCollector,
    'sla_plus': SlaPlusCollector,
    'top_hosts': TopHostsCollector,
    'top_problems': TopProblemsCollector,
    'stress': StressCollector,
    'wifi': WiFiCollector,
}


# Task manager
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
            raise ValueError("Configuracao do Zabbix nao encontrada ou token invalido.")

    def _update_status(self, message):
        update_status(self.task_id, message)

    # -------------------- SLA helper --------------------
    def _get_client_sla_contract(self):
        try:
            current_app.logger.debug(
                f"[ReportGenerator] Buscando SLA do cliente id={getattr(self.client, 'id', 'N/A')}"
            )
            for attr in ("sla_contract", "sla", "sla_policy", "sla_plan", "sla_goal"):
                val = getattr(self.client, attr, None)
                if val is not None:
                    try:
                        return float(val)
                    except Exception:
                        return val
        except Exception as e:
            current_app.logger.warning("[ReportGenerator] Falha ao inspecionar SLA no Client", exc_info=True)
        fallback = None
        try:
            if isinstance(self.system_config, dict):
                fallback = self.system_config.get("DEFAULT_SLA_CONTRACT")
            else:
                fallback = getattr(self.system_config, "DEFAULT_SLA_CONTRACT", None)
        except Exception:
            pass
        if fallback is not None:
            try:
                return float(fallback)
            except Exception:
                return fallback
        current_app.logger.warning("[ReportGenerator] Nenhuma meta de SLA definida para o cliente")
        return None

    # -------------------- Pipeline --------------------
    def generate(self, client, ref_month_str, system_config, author, report_layout_json):
        self.client = client
        self.system_config = system_config
        self.cached_data = {}

        self._update_status("Iniciando geracao do relatorio.")

        # Periodo
        try:
            ref_date = dt.datetime.strptime(f"{ref_month_str}-01", "%Y-%m-%d")
        except ValueError:
            return None, "Formato de mes de referencia invalido. Use YYYY-MM."
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0)
        end_date = (start_date.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(seconds=1)
        period = {"start": int(start_date.timestamp()), "end": int(end_date.timestamp())}

        # Grupos do cliente
        try:
            groups_rel = client.zabbix_groups.all() if hasattr(client.zabbix_groups, "all") else client.zabbix_groups
            group_ids = [g.group_id for g in groups_rel if getattr(g, "group_id", None)]
        except Exception as e:
            current_app.logger.error(f"[ReportGenerator.generate] Falha ao obter grupos do cliente {client.id}: {e}", exc_info=True)
            group_ids = []
        if not group_ids:
            return None, f"O cliente '{client.name}' nao possui Grupos Zabbix associados."

        # Hosts
        self._update_status("Coletando hosts do cliente...")
        all_hosts = self.get_hosts(group_ids)
        if not all_hosts:
            return None, f"Nenhum host encontrado para os grupos Zabbix do cliente {client.name}."
        self.cached_data['all_hosts'] = all_hosts

        # Layout
        try:
            report_layout = json.loads(report_layout_json) if isinstance(report_layout_json, str) else report_layout_json
        except Exception as e:
            current_app.logger.error("[ReportGenerator.generate] Layout JSON invalido", exc_info=True)
            return None, "Layout invalido (JSON)."

        availability_data_cache = None
        sla_prev_month_df = None
        availability_module_types = {
            'sla', 'sla_table', 'sla_chart', 'sla_plus', 'kpi', 'top_hosts', 'top_problems', 'stress'
        }
        final_html_parts = []

        # Pre-collect SLA if needed
        if any(mod.get('type') in availability_module_types for mod in (report_layout or [])):
            self._update_status("Coletando dados de disponibilidade (SLA)...")
            sla_contract = self._get_client_sla_contract()
            try:
                availability_data_cache, error_msg = self._collect_availability_data(all_hosts, period, sla_contract)
            except Exception as e:
                current_app.logger.error("[ReportGenerator.generate] Falha na pre-coleta de SLA", exc_info=True)
                final_html_parts.append("<p>Erro critico ao coletar dados de disponibilidade.</p>")
                availability_data_cache, error_msg = {}, "pre-coleta falhou"
            if error_msg:
                current_app.logger.warning(f"[ReportGenerator.generate] Erro SLA primario: {error_msg}")
                final_html_parts.append(f"<p>Erro critico ao coletar dados de disponibilidade: {error_msg}</p>")
                availability_data_cache = {}

        # Previous month (for legacy SLA)
        sla_module_config = next((m for m in (report_layout or []) if m.get('type') == 'sla'), None)
        if sla_module_config and availability_data_cache:
            custom_options = sla_module_config.get('custom_options', {})
            if custom_options.get('compare_to_previous_month'):
                self._update_status("Coletando dados do mes anterior para comparacao de SLA.")
                prev_ref_date = ref_date - dt.timedelta(days=1)
                prev_month_start = prev_ref_date.replace(day=1)
                prev_month_end = (prev_month_start.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(seconds=1)
                prev_period = {'start': int(prev_month_start.timestamp()), 'end': int(prev_month_end.timestamp())}
                sla_contract = self._get_client_sla_contract()
                try:
                    prev_data, prev_error = self._collect_availability_data(all_hosts, prev_period, sla_contract, trends_only=True)
                except Exception as e:
                    current_app.logger.error("[ReportGenerator.generate] Falha ao coletar mes anterior", exc_info=True)
                    prev_data, prev_error = None, "erro coleta mes anterior"
                if not prev_error and prev_data and 'df_sla_problems' in prev_data:
                    sla_prev_month_df = prev_data['df_sla_problems'].rename(columns={'SLA (%)': 'SLA_anterior'})
                    self.cached_data['prev_month_sla_df'] = prev_data['df_sla_problems']

        # Assemble modules
        for module_config in (report_layout or []):
            module_type = module_config.get('type')
            collector_class = COLLECTOR_MAP.get(module_type)
            if not collector_class:
                self._update_status(f"Aviso: Nenhum plugin encontrado para o tipo '{module_type}'.")
                continue
            try:
                collector_instance = collector_class(self, module_config)
                if module_type in availability_module_types:
                    if availability_data_cache:
                        if module_type in {'sla', 'sla_table', 'sla_chart', 'sla_plus'}:
                            html_part = collector_instance.collect(all_hosts, period, availability_data_cache, df_prev_month=sla_prev_month_df)
                        else:
                            html_part = collector_instance.collect(all_hosts, period, availability_data_cache)
                    else:
                        html_part = "<p>Dados de disponibilidade indisponiveis para este modulo.</p>"
                else:
                    html_part = collector_instance.collect(all_hosts, period)
                final_html_parts.append(html_part)
            except Exception as e:
                current_app.logger.error(f"Erro ao executar o plugin '{module_type}': {e}", exc_info=True)
                final_html_parts.append(f"<p>Erro critico ao processar modulo '{module_type}'.</p>")

        # Render HTML and build PDF
        dados_gerais = {
            'group_name': client.name,
            'periodo_referencia': start_date.strftime('%B de %Y').capitalize(),
            'data_emissao': dt.datetime.now().strftime('%d/%m/%Y'),
            'report_content': ''.join(final_html_parts)
        }
        try:
            miolo_html = render_template('_MIOLO_BASE.html', **dados_gerais, modules={'pandas': pd})
        except Exception as e:
            current_app.logger.error("[ReportGenerator.generate] Falha ao renderizar HTML", exc_info=True)
            return None, "Falha ao renderizar o conteudo do relatorio."

        self._update_status("Montando o relatorio final.")
        try:
            pdf_builder = PDFBuilder(self.task_id)
            err = pdf_builder.add_cover_page(system_config.report_cover_path)
            if err:
                return None, err
            err = pdf_builder.add_miolo_from_html(miolo_html)
            if err:
                return None, err
            err = pdf_builder.add_final_page(system_config.report_final_page_path)
            if err:
                return None, err
        except Exception as e:
            current_app.logger.error("[ReportGenerator.generate] Falha ao montar PDF", exc_info=True)
            return None, "Falha ao montar o PDF do relatorio."

        pdf_filename = f"Relatorio_Custom_{client.name.replace(' ', '_')}_{ref_month_str}_{os.urandom(4).hex()}.pdf"
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
        AuditService.log(f"Gerou relatorio customizado para '{client.name}' referente a {ref_month_str}", user=author)
        return pdf_path, None

    # -------------------- Availability data --------------------
    def _collect_availability_data(self, all_hosts, period, sla_goal, trends_only=False):
        all_host_ids = [h['hostid'] for h in all_hosts]
        # icmpping items with triggers (to correlate problems)
        ping_items = self.get_items(all_host_ids, 'icmpping', search_by_key=True, include_triggers=True)
        if not ping_items:
            return None, "Nenhum item 'icmpping' encontrado."
        hosts_with_ping_ids = {it['hostid'] for it in ping_items}
        hosts_for_sla = [h for h in all_hosts if h['hostid'] in hosts_with_ping_ids]
        if not hosts_for_sla:
            return None, "Nenhum host com PING para calcular SLA."
        ping_trigger_ids = list({t['triggerid'] for it in ping_items for t in (it.get('triggers') or [])})
        if not ping_trigger_ids:
            return None, "Nenhum trigger de PING encontrado."

        ping_events = self.obter_eventos_wrapper(ping_trigger_ids, period, 'objectids')
        if ping_events is None:
            return None, "Falha ao coletar eventos de PING."

        ping_problems = [p for p in ping_events if p.get('source') == '0' and p.get('object') == '0' and p.get('value') == '1']
        correlated = self._correlate_problems(ping_problems, ping_events, period)
        df_sla = pd.DataFrame(self._calculate_sla(correlated, hosts_for_sla, period))

        if trends_only:
            return {'df_sla_problems': df_sla}, None

        # Count problems for all hosts (group scope)
        all_group_events = self.obter_eventos_wrapper(all_host_ids, period, 'hostids')
        if all_group_events is None:
            return None, "Falha ao coletar eventos do grupo."
        all_problems = [p for p in all_group_events if p.get('source') == '0' and p.get('object') == '0' and p.get('value') == '1']

        # Constrói dataframe detalhado de incidentes por host/problema/clock
        host_map = {str(h['hostid']): h['nome_visivel'] for h in (all_hosts or [])}
        detailed_rows = []
        severity_counts = {}
        sev_map = {
            '0': 'Não Classificado', '1': 'Informação', '2': 'Atenção',
            '3': 'Média', '4': 'Alta', '5': 'Desastre'
        }
        for ev in (all_problems or []):
            try:
                hosts = ev.get('hosts') or []
                hostid = str((hosts[0] or {}).get('hostid')) if hosts else None
                host_name = host_map.get(hostid, f'Host {hostid}') if hostid else 'Desconhecido'
                prob_name = ev.get('name') or f"Trigger {ev.get('objectid') or ev.get('triggerid') or '?'}"
                clk = int(ev.get('clock', 0))
                detailed_rows.append({'Host': host_name, 'Problema': prob_name, 'Ocorrências': 1, 'clock': clk})
                sev_raw = ev.get('severity', 'Desconhecido')
                sev_key = sev_map.get(str(sev_raw), 'Desconhecido')
                severity_counts[sev_key] = severity_counts.get(sev_key, 0) + 1
            except Exception:
                continue
        import pandas as _pd
        df_top_incidents = _pd.DataFrame(detailed_rows, columns=['Host', 'Problema', 'Ocorrências', 'clock']) if detailed_rows else _pd.DataFrame(columns=['Host', 'Problema', 'Ocorrências', 'clock'])

        # KPIs em lista (conforme coletor KPI)
        avg_sla = float(df_sla['SLA (%)'].mean()) if not df_sla.empty else 100.0
        total_hosts = len(self.cached_data.get('all_hosts', [])) or len(all_hosts)
        try:
            goal = float(sla_goal) if sla_goal is not None else None
        except Exception:
            goal = None
        try:
            hosts_ok = int(df_sla[df_sla.get('SLA (%)', _pd.Series(dtype=float)) >= float(goal if goal is not None else 100)].shape[0]) if not df_sla.empty else 0
        except Exception:
            hosts_ok = 0
        top_offender = None
        try:
            if not df_top_incidents.empty:
                top_offender = df_top_incidents.groupby('Host')['Ocorrências'].sum().sort_values(ascending=False).index.tolist()[0]
        except Exception:
            top_offender = None
        kpis_data = [
            {'label': 'Média de SLA', 'value': f"{avg_sla:.2f}%", 'sublabel': 'Mês atual', 'trend': None, 'status': 'atingido' if (goal and avg_sla >= float(goal)) else 'nao-atingido'},
            {'label': 'Hosts com SLA', 'value': f"{hosts_ok}/{total_hosts}", 'sublabel': 'SLA >= meta', 'trend': None, 'status': 'ok' if hosts_ok == total_hosts and total_hosts > 0 else 'info'},
            {'label': 'Total de Incidentes', 'value': str(int(df_top_incidents['Ocorrências'].sum())) if not df_top_incidents.empty else '0', 'sublabel': 'no período', 'trend': None, 'status': 'info'},
            {'label': 'Principal Ofensor', 'value': top_offender or '—', 'sublabel': 'mais incidentes', 'trend': None, 'status': 'critico' if top_offender else 'info'},
        ]

        return {'df_sla_problems': df_sla, 'df_top_incidents': df_top_incidents, 'kpis': kpis_data, 'severity_counts': severity_counts}, None

    # -------------------- Helpers --------------------
    def _normalize_string(self, s):
        return re.sub(r"\s+", " ", str(s).replace("\n", " ").replace("\r", " ")).strip()

    def get_hosts(self, groupids):
        self._update_status("Coletando dados de hosts.")
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
            lat_trends = self.get_trends([it['itemid'] for it in lat_items], period['start'], period['end'])
            df_lat = self._process_trends(lat_trends, lat_items, host_map, unit_conversion_factor=1000)
        loss_items = self.get_items(host_ids, 'icmppingloss', search_by_key=True)
        df_loss = pd.DataFrame()
        if loss_items:
            loss_trends = self.get_trends([it['itemid'] for it in loss_items], period['start'], period['end'])
            df_loss = self._process_trends(loss_trends, loss_items, host_map)
        if df_lat.empty and df_loss.empty:
            return None, "Nenhum item de icmppingsec/icmppingloss encontrado."
        return {'df_lat': df_lat, 'df_loss': df_loss}, None

    # -------------- Zabbix data access --------------
    def get_items(self, hostids, filter_key, search_by_key=False, exact_key_search=False, include_triggers=False):
        self._update_status(f"Buscando itens com filtro '{filter_key}'.")
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
        body = {'jsonrpc': '2.0', 'method': 'item.get', 'params': params, 'auth': self.token, 'id': 1}
        return fazer_request_zabbix(body, self.url) or []

    def get_trends(self, itemids, time_from=None, time_till=None):
        if isinstance(time_from, dict) and time_till is None:
            period = time_from
            time_from = int(period.get('start'))
            time_till = int(period.get('end'))
            current_app.logger.debug("[ReportGenerator.get_trends] Back-compat: period dict.")
        if time_from is None or time_till is None:
            raise TypeError("get_trends requires time_from and time_till or a period dict as second arg.")
        self._update_status(f"Buscando tendencias para {len(itemids)} itens.")
        body = {
            'jsonrpc': '2.0', 'method': 'trend.get',
            'params': {
                'output': ['itemid', 'clock', 'num', 'value_min', 'value_avg', 'value_max'],
                'itemids': itemids,
                'time_from': int(time_from),
                'time_till': int(time_till)
            },
            'auth': self.token, 'id': 1
        }
        trends = fazer_request_zabbix(body, self.url)
        if not isinstance(trends, list):
            current_app.logger.error("Falha ao buscar trends: resposta invalida do Zabbix.")
            return []
        return trends

    def get_trends_chunked(self, itemids, time_from, time_till, chunk_size=150):
        """
        Busca trends em lotes menores para evitar sobrecarga/erros 500 no Zabbix.
        """
        if not itemids:
            return []
        all_trends = []
        items_list = list(itemids)
        total = len(items_list)
        for i in range(0, total, int(chunk_size)):
            chunk = items_list[i:i+int(chunk_size)]
            try:
                self._update_status(f"Buscando trends em lote {i+1}-{min(i+len(chunk), total)} de {total}...")
                part = self.get_trends(chunk, time_from, time_till)
                if isinstance(part, list) and part:
                    all_trends.extend(part)
            except Exception:
                current_app.logger.warning("Falha em um lote de trend.get; seguindo para o proximo.", exc_info=True)
                continue
        return all_trends

    def _iter_chunks(self, seq, size):
        for i in range(0, len(seq), size):
            yield seq[i:i + size]

    def _process_trends(self, trends, items, host_map, unit_conversion_factor=1, is_pavailable=False, agg_method='mean'):
        if not isinstance(trends, list) or not trends:
            return pd.DataFrame(columns=['Host', 'Min', 'Max', 'Avg'])
        df = pd.DataFrame(trends)
        df[['value_min', 'value_avg', 'value_max']] = df[['value_min', 'value_avg', 'value_max']].astype(float)
        item_to_host_map = {str(item['itemid']): item['hostid'] for item in items}
        df['itemid'] = df['itemid'].astype(str)
        df['hostid'] = df['itemid'].map(item_to_host_map)
        agg_functions = {
            'Min': ('value_min', agg_method),
            'Max': ('value_max', agg_method),
            'Avg': ('value_avg', agg_method)
        }
        out = df.groupby('hostid').agg(**agg_functions).reset_index()
        if is_pavailable:
            out['Min_old'], out['Max_old'] = out['Min'], out['Max']
            out['Min'], out['Max'] = 100 - out['Max_old'], 100 - out['Min_old']
            out['Avg'] = 100 - out['Avg']
            out.drop(columns=['Min_old', 'Max_old'], inplace=True)
        for c in ['Min', 'Max', 'Avg']:
            out[c] *= unit_conversion_factor
        out['Host'] = out['hostid'].map(host_map)
        return out[['Host', 'Min', 'Max', 'Avg']]

    # -------------- Trends/History helpers --------------
    def get_history_aggregated(self, itemids, time_from, time_till, value_type=0, agg_method='mean'):
        """
        Fallback para agregar via history.get quando trend.get não retorna dados.
        Retorna uma lista de dicts com chaves: itemid, value_min, value_avg, value_max.
        """
        if not itemids:
            return []
        results = []
        for chunk in self._iter_chunks(list(itemids), 100):
            params = {
                'output': ['itemid', 'clock', 'value'],
                'itemids': chunk,
                'time_from': int(time_from),
                'time_till': int(time_till),
                'history': int(value_type)
            }
            body = {'jsonrpc': '2.0', 'method': 'history.get', 'params': params, 'auth': self.token, 'id': 1}
            data = fazer_request_zabbix(body, self.url)
            if not isinstance(data, list) or not data:
                continue
            try:
                df = pd.DataFrame(data)
                df['itemid'] = df['itemid'].astype(str)
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                agg = df.groupby('itemid')['value'].agg(value_min='min', value_avg=agg_method, value_max='max').reset_index()
                results.extend(agg.to_dict('records'))
            except Exception:
                continue
        return results

    def get_trends_with_fallback(self, itemids, time_from, time_till, history_value_type=0, agg_method='mean'):
        """Tenta trend.get (em lotes); se vazio, usa history.get agregado."""
        trends = self.get_trends_chunked(itemids, time_from, time_till)
        if isinstance(trends, list) and trends:
            return trends
        return self.get_history_aggregated(itemids, time_from, time_till, value_type=history_value_type, agg_method=agg_method)

    def robust_aggregate(self, itemids, time_from, time_till, items_meta=None, chunk_size=None):
        """
        API usada pelos coletores resilientes (CPU/Mem/Disk): retorna estrutura tipo trends
        (itemid, value_min, value_avg, value_max), usando trend.get e fallback para history.get com value_type
        inferido quando possível a partir de items_meta.
        """
        if not itemids:
            return []
        trends = self.get_trends_chunked(itemids, time_from, time_till, chunk_size=chunk_size or 150)
        if isinstance(trends, list) and trends:
            return trends
        vt = 0
        try:
            if items_meta:
                vts = [int((it.get('value_type', 0))) for it in items_meta if it is not None]
                if vts:
                    vt = max(set(vts), key=vts.count)
        except Exception:
            vt = 0
        return self.get_history_aggregated(itemids, time_from, time_till, value_type=vt)

    # -------------------- Events --------------------
    def obter_eventos(self, object_ids, periodo, id_type='hostids', max_depth=3):
        time_from, time_till = periodo['start'], periodo['end']
        if max_depth <= 0:
            current_app.logger.error("Limite de profundidade atingido em obter_eventos.")
            return None
        params = {
            'output': 'extend',
            'selectHosts': ['hostid'],
            'time_from': time_from,
            'time_till': time_till,
            id_type: object_ids,
            'sortfield': ['eventid'],
            'sortorder': 'ASC',
            'select_acknowledges': 'extend'
        }
        body = {'jsonrpc': '2.0', 'method': 'event.get', 'params': params, 'auth': self.token, 'id': 1}
        resposta = fazer_request_zabbix(body, self.url, allow_retry=False)
        if isinstance(resposta, dict) and 'error' in resposta:
            self._update_status("Consulta pesada detectada, quebrando o periodo.")
            mid = time_from + (time_till - time_from) // 2
            p1 = {'start': time_from, 'end': mid}
            p2 = {'start': mid + 1, 'end': time_till}
            e1 = self.obter_eventos(object_ids, p1, id_type, max_depth - 1)
            if e1 is None:
                return None
            e2 = self.obter_eventos(object_ids, p2, id_type, max_depth - 1)
            if e2 is None:
                return None
            return e1 + e2
        return resposta

    def obter_eventos_wrapper(self, object_ids, periodo, id_type='objectids'):
        if not object_ids:
            return []
        self._update_status(f"Processando eventos para {len(object_ids)} objetos em uma unica chamada...")
        evs = self.obter_eventos(object_ids, periodo, id_type)
        if evs is None:
            current_app.logger.critical("Falha critica ao coletar eventos.")
            return None
        return sorted(evs, key=lambda x: int(x['clock']))

    def _correlate_problems(self, problems, all_events, period=None):
        if not problems:
            return []
        events_by_trigger = defaultdict(list)
        for ev in (all_events or []):
            tid = ev.get('objectid') or ev.get('triggerid')
            if tid is not None:
                events_by_trigger[str(tid)].append(ev)
        for evs in events_by_trigger.values():
            evs.sort(key=lambda e: int(e.get('clock', 0)))
        out = []
        for p in problems:
            try:
                tid = str(p.get('objectid') or p.get('triggerid'))
                evs = events_by_trigger.get(tid, [])
                p_clock = int(p.get('clock'))
                hostid = None
                hosts = p.get('hosts') or []
                if hosts:
                    hostid = (hosts[0] or {}).get('hostid')
                end_clock = None
                for ev in evs:
                    if int(ev.get('clock', 0)) > p_clock and str(ev.get('value', '0')) == '0':
                        end_clock = int(ev['clock'])
                        break
                if end_clock is None:
                    if period and 'end' in period:
                        try:
                            end_clock = int(period['end'])
                        except Exception:
                            end_clock = None
                if end_clock is None and evs:
                    end_clock = int(evs[-1].get('clock', p_clock))
                if end_clock is None:
                    end_clock = p_clock
                out.append({'triggerid': tid, 'hostid': hostid, 'start': p_clock, 'end': max(end_clock, p_clock)})
            except Exception:
                continue
        return out

    def _calculate_sla(self, correlated_problems, hosts_for_sla, period):
        if not hosts_for_sla:
            return []
        host_map = {str(h['hostid']): h['nome_visivel'] for h in hosts_for_sla}
        p_start = int(period['start'])
        p_end = int(period['end'])
        total = max(1, p_end - p_start)
        downtime = {str(h['hostid']): 0 for h in hosts_for_sla}
        for pr in (correlated_problems or []):
            hid = str(pr.get('hostid')) if pr.get('hostid') is not None else None
            if hid not in downtime:
                continue
            s = max(p_start, int(pr.get('start', p_start)))
            e = min(p_end, int(pr.get('end', p_end)))
            if e > s:
                downtime[hid] += (e - s)
        rows = []
        for hid, d in downtime.items():
            sla = max(0.0, min(100.0, 100.0 * (1.0 - (d / total))))
            try:
                hours = int(d // 3600)
                minutes = int((d % 3600) // 60)
                seconds = int(d % 60)
                downtime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except Exception:
                downtime_str = "00:00:00"
            rows.append({
                'Host': host_map.get(hid, f'Host {hid}'),
                'SLA (%)': float(sla),
                'Tempo Indisponível': downtime_str,
                'Downtime (s)': int(d)
            })
        return rows

    def _count_problems_by_host(self, problems, all_hosts):
        host_map = {str(h['hostid']): h['nome_visivel'] for h in (all_hosts or [])}
        cnt = defaultdict(int)
        for p in (problems or []):
            hosts = p.get('hosts') or []
            if hosts:
                hid = str((hosts[0] or {}).get('hostid'))
                cnt[hid] += 1
        import pandas as pd
        rows = [{'Host': host_map.get(h, f'Host {h}'), 'Problemas': c} for h, c in cnt.items()]
        return pd.DataFrame(rows)
