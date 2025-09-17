from .base_collector import BaseCollector
import datetime
import pandas as pd

class UptimeSummaryCollector(BaseCollector):
    """
    Módulo Resumo de Disponibilidade (Uptime).

    Coleta dados de SLA de serviços do Zabbix ou calcula a disponibilidade
    baseado em triggers para gerar uma visão rica do uptime dos hosts.
    """

    def _format_duration(self, seconds):
        if seconds is None or not isinstance(seconds, (int, float)) or seconds < 0:
            return "N/A"
        try:
            seconds = int(seconds)
            days, rem = divmod(seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, secs = divmod(rem, 60)
            parts = []
            if days: parts.append(f"{days}d")
            if hours: parts.append(f"{hours}h")
            if minutes: parts.append(f"{minutes}m")
            if secs or not parts: parts.append(f"{secs}s")
            return " ".join(parts)
        except Exception:
            return "Inválido"

    def _get_status_color(self, sli, threshold_crit, threshold_warn):
        try:
            sli_f = float(sli)
            if sli_f < float(threshold_crit):
                return 'danger' # Vermelho
            if sli_f < float(threshold_warn):
                return 'warning' # Amarelo
            return 'success' # Verde
        except (ValueError, TypeError):
            return 'secondary' # Cinza

    def collect(self, all_hosts, period):
        opts = self.module_config.get('custom_options', {})

        # Opções de customização da UI
        host_contains = (opts.get('host_name_contains') or '').strip().lower()
        sla_target = opts.get('sla_target', 99.9)
        threshold_warn = opts.get('threshold_warning', 99.95)
        threshold_crit = opts.get('threshold_critical', 99.9)
        sort_by = opts.get('sort_by', 'hostname_asc')
        zabbix_service_tag = opts.get('zabbix_service_tag') # Filtro por tag de serviço

        # Filtra hosts pelo nome, se especificado
        if host_contains:
            all_hosts = [h for h in all_hosts if host_contains in h.get('nome_visivel', '').lower()]

        all_host_ids = [h['hostid'] for h in all_hosts]
        if not all_host_ids:
            return self.render('uptime_summary', {"hosts_data": []})

        # --- Ponto Chave: Obtenção de Dados ---
        # Você precisará de uma função no seu `generator` que busque os dados de SLA.
        # Esta função é a peça mais importante a ser implementada no seu backend.
        # Exemplo: self.generator.obter_disponibilidade_sla(host_ids, period, service_tag)
        try:
            availability_data = self.generator.obter_disponibilidade_sla(
                host_ids=all_host_ids,
                period=period,
                service_tag=zabbix_service_tag
            )
            if availability_data is None:
                raise ConnectionError("A função obter_disponibilidade_sla retornou None.")
        except Exception as e:
            self._update_status(f"Erro ao chamar obter_disponibilidade_sla: {e}")
            return self.render('uptime_summary', {"error": f"Não foi possível coletar dados de disponibilidade. Verifique a integração com o Zabbix. Detalhe: {e}"})

        if not availability_data:
            return self.render('uptime_summary', {"hosts_data": []})

        processed_hosts = []
        period_duration = period['end'] - period['start']

        host_name_map = {h['hostid']: h.get('nome_visivel', f"HostID {h['hostid']}") for h in all_hosts}

        for host_id, data in availability_data.items():
            sli = data.get('sli', 100.0)
            downtimes = data.get('downtimes', []) # Lista de dicts {'start': ts, 'end': ts}

            total_downtime_sec = sum(d.get('duration', 0) for d in downtimes)
            longest_downtime_sec = max(d.get('duration', 0) for d in downtimes) if downtimes else 0

            # Prepara a linha do tempo
            timeline_events = []
            for dt in downtimes:
                start_offset = dt['start'] - period['start']
                duration = dt['end'] - dt['start']
                timeline_events.append({
                    'left_percent': max(0, start_offset / period_duration * 100),
                    'width_percent': min(100, duration / period_duration * 100),
                    'tooltip': f"Início: {datetime.datetime.fromtimestamp(dt['start']).strftime('%d/%m %H:%M')}\nDuração: {self._format_duration(duration)}"
                })

            processed_hosts.append({
                'host_name': host_name_map.get(host_id, f"HostID {host_id}"),
                'sli': f"{sli:.4f}",
                'sla_target': sla_target,
                'status_color': self._get_status_color(sli, threshold_crit, threshold_warn),
                'total_downtime': self._format_duration(total_downtime_sec),
                'total_downtime_seconds': total_downtime_sec,
                'incident_count': len(downtimes),
                'longest_downtime': self._format_duration(longest_downtime_sec),
                'timeline_events': timeline_events,
            })

        # Ordenação
        if sort_by == 'uptime_asc':
            processed_hosts.sort(key=lambda x: float(x['sli']))
        elif sort_by == 'downtime_desc':
            processed_hosts.sort(key=lambda x: x['total_downtime_seconds'], reverse=True)
        else: # hostname_asc
            processed_hosts.sort(key=lambda x: x['host_name'])

        return self.render('uptime_summary', {
            "hosts_data": processed_hosts,
            "period_start_str": datetime.datetime.fromtimestamp(period['start']).strftime('%d/%m/%Y'),
            "period_end_str": datetime.datetime.fromtimestamp(period['end']).strftime('%d/%m/%Y'),
        })