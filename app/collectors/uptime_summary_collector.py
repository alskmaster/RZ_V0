from .base_collector import BaseCollector
import datetime


class UptimeSummaryCollector(BaseCollector):
    """Uptime summary module with per-host incident summary."""

    _SEVERITY_LABELS = {
        '0': 'Não Classificado',
        '1': 'Informação',
        '2': 'Atenção',
        '3': 'Média',
        '4': 'Alta',
        '5': 'Desastre'
    }

    def _format_duration(self, seconds):
        if seconds is None or not isinstance(seconds, (int, float)) or seconds < 0:
            return "N/A"
        try:
            seconds = int(seconds)
            days, rem = divmod(seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, secs = divmod(rem, 60)
            parts = []
            if days:
                parts.append(f"{days}d")
            if hours:
                parts.append(f"{hours}h")
            if minutes:
                parts.append(f"{minutes}m")
            if secs or not parts:
                parts.append(f"{secs}s")
            return " ".join(parts)
        except Exception:
            return "Invalido"

    def _get_status_color(self, sli, threshold_crit, threshold_warn):
        try:
            sli_f = float(sli)
            if sli_f < float(threshold_crit):
                return 'danger'
            if sli_f < float(threshold_warn):
                return 'warning'
            return 'success'
        except (ValueError, TypeError):
            return 'secondary'

    def _to_float(self, value, default):
        try:
            if value is None:
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _format_sli_display(self, value):
        try:
            val = float(value)
        except (TypeError, ValueError):
            return 'N/A'
        if abs(val - 100.0) < 1e-6:
            return '100%'
        return f"{val:.2f}%"

    def collect(self, all_hosts, period):
        opts = self.module_config.get('custom_options', {}) or {}

        host_contains = (opts.get('host_name_contains') or '').strip().lower()
        zabbix_service_tag = (opts.get('zabbix_service_tag') or '').strip() or None
        sort_by = (opts.get('sort_by') or 'hostname_asc').lower()

        contract_target = None
        try:
            contract_target = float(self.generator._get_client_sla_contract())
        except Exception:
            contract_target = None
        default_target = contract_target if contract_target is not None else 99.9
        sla_target = self._to_float(opts.get('sla_target'), default_target)
        warn_default = default_target if contract_target is not None else 99.95
        warn_default = min(warn_default, sla_target)
        crit_default = default_target if contract_target is not None else 99.9
        crit_default = min(crit_default, warn_default)
        threshold_warn = self._to_float(opts.get('threshold_warning'), warn_default)
        threshold_crit = self._to_float(opts.get('threshold_critical'), crit_default)

        if host_contains:
            all_hosts = [h for h in all_hosts if host_contains in str(h.get('nome_visivel', '')).lower()]

        all_host_ids = [str(h['hostid']) for h in all_hosts if h.get('hostid') is not None]
        if not all_host_ids:
            return self.render('uptime_summary', {"hosts_data": []})

        period_start = int(period.get('start')) if isinstance(period, dict) else 0
        period_end = int(period.get('end')) if isinstance(period, dict) else 0

        try:
            availability_data = self.generator.obter_disponibilidade_sla(
                host_ids=all_host_ids,
                period={'start': period_start, 'end': period_end},
                service_tag=zabbix_service_tag,
            )
            if availability_data is None:
                raise ConnectionError("obter_disponibilidade_sla returned None")
        except Exception as exc:
            self._update_status(f"uptime_summary | falha ao coletar SLA: {exc}")
            return self.render('uptime_summary', {
                "error": "Nao foi possivel coletar dados de disponibilidade. Verifique a integracao com o Zabbix.",
            })

        if not availability_data:
            return self.render('uptime_summary', {"hosts_data": []})

        host_name_map = {str(h['hostid']): h.get('nome_visivel', f"HostID {h['hostid']}") for h in all_hosts}
        processed_hosts = []

        for host_id in all_host_ids:
            data = availability_data.get(str(host_id), {})
            sli_val = data.get('sli', 100.0)
            try:
                sli_num = float(sli_val)
            except (TypeError, ValueError):
                sli_num = 0.0
            downtimes = data.get('downtimes', []) or []
            incidents_raw = data.get('incidents', []) or []

            total_downtime_sec = 0
            longest_downtime_sec = 0
            incident_entries = []

            for dt_entry in downtimes:
                try:
                    start_ts = int(dt_entry.get('start', period_start))
                    end_ts = int(dt_entry.get('end', start_ts))
                except Exception:
                    continue
                if end_ts < start_ts:
                    end_ts = start_ts
                duration = int(dt_entry.get('duration', end_ts - start_ts))
                if duration < 0:
                    duration = 0
                total_downtime_sec += duration
                if duration > longest_downtime_sec:
                    longest_downtime_sec = duration

            for incident in incidents_raw:
                try:
                    start_ts = int(incident.get('start', period_start))
                except Exception:
                    start_ts = period_start
                try:
                    end_ts = int(incident.get('end', start_ts))
                except Exception:
                    end_ts = start_ts
                if end_ts < start_ts:
                    end_ts = start_ts
                duration = int(incident.get('duration', end_ts - start_ts))
                if duration < 0:
                    duration = 0
                incident_entries.append({
                    'start_str': datetime.datetime.fromtimestamp(start_ts).strftime('%d/%m %H:%M'),
                    'end_str': datetime.datetime.fromtimestamp(end_ts).strftime('%d/%m %H:%M'),
                    'duration': self._format_duration(duration),
                    'severity': self._SEVERITY_LABELS.get(str(incident.get('severity')), 'Desconhecido'),
                    'name': incident.get('name') or 'N/A',
                })

            processed_hosts.append({
                'host_name': host_name_map.get(str(host_id), f"HostID {host_id}"),
                'sli_value': sli_num,
                'sli_display': self._format_sli_display(sli_num),
                'sla_target': sla_target,
                'status_color': self._get_status_color(sli_num, threshold_crit, threshold_warn),
                'total_downtime': self._format_duration(total_downtime_sec),
                'total_downtime_seconds': total_downtime_sec,
                'incident_count': len(incident_entries) if incident_entries else len(downtimes),
                'longest_downtime': self._format_duration(longest_downtime_sec),
                'incidents': incident_entries,
            })

        if sort_by == 'uptime_asc':
            processed_hosts.sort(key=lambda item: float(item.get('sli_value') if item.get('sli_value') is not None else 0.0))
        elif sort_by == 'downtime_desc':
            processed_hosts.sort(key=lambda item: item.get('total_downtime_seconds', 0), reverse=True)
        else:
            processed_hosts.sort(key=lambda item: str(item.get('host_name', '')))

        return self.render('uptime_summary', {
            "hosts_data": processed_hosts,
            "period_start_str": datetime.datetime.fromtimestamp(period_start).strftime('%d/%m/%Y'),
            "period_end_str": datetime.datetime.fromtimestamp(period_end).strftime('%d/%m/%Y'),
        })
