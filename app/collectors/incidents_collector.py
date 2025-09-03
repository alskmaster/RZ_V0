# app/collectors/incidents_collector.py
from .base_collector import BaseCollector
import datetime
import pandas as pd

class IncidentsCollector(BaseCollector):
    """
    Módulo de Incidentes.
    Coleta e exibe incidentes (problemas) do Zabbix, agrupados por host e filtráveis por severidade.
    """

    def _format_timestamp(self, timestamp):
        """
        Converte um timestamp Unix para uma string de data/hora formatada.
        """
        if not timestamp:
            return "N/A"
        try:
            return datetime.datetime.fromtimestamp(int(timestamp)).strftime('%d/%m/%Y %H:%M:%S')
        except (ValueError, TypeError):
            return "Inválido"

    def _format_duration(self, seconds):
        """
        Converte uma duração em segundos para uma string legível (ex: 1d 2h 30m 15s).
        """
        if not seconds:
            return "0s"
        try:
            seconds = int(seconds)
            if seconds < 0: # Lidar com durações negativas, se houver
                return "N/A"
            
            days = seconds // (24 * 3600)
            seconds %= (24 * 3600)
            hours = seconds // 3600
            seconds %= 3600
            minutes = seconds // 60
            seconds %= 60

            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            if minutes > 0:
                parts.append(f"{minutes}m")
            if seconds > 0 or not parts: # Incluir segundos se houver, ou se for 0s
                parts.append(f"{seconds}s")
            
            return " ".join(parts)
        except (ValueError, TypeError):
            return "Inválido"

    def collect(self, all_hosts, period):
        """
        Método principal para coletar dados de incidentes e renderizar o HTML.
        """
        severity_map = {
            '0': 'Não Classificado',
            '1': 'Informação',
            '2': 'Atenção',
            '3': 'Média',
            '4': 'Alta',
            '5': 'Desastre'
        }

        severity_filter_map = {
            'info': '1',
            'warning': '2',
            'average': '3',
            'high': '4',
            'disaster': '5',
            'not_classified': '0'
        }

        custom_options = self.module_config.get('custom_options', {})
        selected_severities_names = custom_options.get('severities', ['info', 'warning', 'average', 'high', 'disaster'])
        selected_severity_ids = [severity_filter_map[s] for s in selected_severities_names if s in severity_filter_map]

        # New Customization: Period Sub-filter
        period_sub_filter = custom_options.get('period_sub_filter', 'full_month')
        start_timestamp = period['start']
        end_timestamp = period['end']

        if period_sub_filter == 'last_24h':
            end_timestamp = int(datetime.datetime.now().timestamp())
            start_timestamp = end_timestamp - (24 * 3600)
        elif period_sub_filter == 'last_7d':
            end_timestamp = int(datetime.datetime.now().timestamp())
            start_timestamp = end_timestamp - (7 * 24 * 3600)
        
        # Adjust period for Zabbix API call
        adjusted_period = {'start': start_timestamp, 'end': end_timestamp}

        all_host_ids = [h['hostid'] for h in all_hosts]
        problems = self.generator.obter_eventos_wrapper(all_host_ids, adjusted_period, 'hostids')

        if problems is None:
            self.generator._update_status("Erro ao coletar eventos de incidentes.")
            return self.render("incidents", {"error": "Não foi possível coletar dados de incidentes."})

        # Converter para DataFrame
        df_problems = pd.DataFrame(problems)

        # Filtrar problemas (value=1, source=0, object=0) e por severidade
        if not df_problems.empty:
            df_problems = df_problems[
                (df_problems['source'] == '0') &
                (df_problems['object'] == '0') &
                (df_problems['value'] == '1') &
                (df_problems['severity'].astype(str).isin(selected_severity_ids))
            ].copy() # Usar .copy() para evitar SettingWithCopyWarning
        else:
            df_problems = pd.DataFrame(columns=['name', 'severity', 'clock', 'r_event', 'acknowledges', 'hosts'])

        if df_problems.empty:
            return self.render("incidents", {
                "hosts_with_incidents": [],
                "selected_severities": selected_severities_names,
                "show_duration": custom_options.get('show_duration', True),
                "show_acknowledgements": custom_options.get('show_acknowledgements', True)
            })

        # Mapear hostids para nomes visíveis
        host_name_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}
        df_problems['host_name'] = df_problems['hosts'].apply(lambda x: host_name_map.get(x[0].get('hostid')) if x and x[0] and x[0].get('hostid') else 'Desconhecido')

        # Formatar colunas para exibição
        df_problems['severity_name'] = df_problems['severity'].astype(str).map(severity_map).fillna('Desconhecido')
        df_problems['formatted_clock'] = df_problems['clock'].apply(self._format_timestamp)
        
        # Robust duration calculation
        df_problems['duration_seconds'] = df_problems.apply(
            lambda row: (int(row['r_event'].get('clock')) - int(row['clock'])) if isinstance(row.get('r_event'), dict) and row['r_event'].get('clock') else 0,
            axis=1
        )
        df_problems['formatted_duration'] = df_problems['duration_seconds'].apply(self._format_duration)
        df_problems['formatted_duration'] = df_problems.apply(
            lambda row: row['formatted_duration'] if row['duration_seconds'] > 0 else 'Em aberto',
            axis=1
        )

        # Process acknowledgements safely
        df_problems['processed_acknowledgements'] = df_problems['acknowledges'].apply(lambda acks:
            [
                {
                    'alias': ack.get('alias', 'N/A'),
                    'message': ack.get('message', 'N/A'),
                    'clock': self._format_timestamp(ack.get('clock', 0))
                }
                for ack in acks if isinstance(acks, list) and isinstance(ack, dict)
            ]
        )

        # New Customization: Primary Grouping
        primary_grouping = custom_options.get('primary_grouping', 'host') # 'host' or 'problem'

        # Agrupar e preparar para o template
        grouped_data = []

        if primary_grouping == 'host':
            # New Customization: Number of Hosts
            num_hosts_to_display = custom_options.get('num_hosts', None)

            # Sort by number of incidents per host (descending) if num_hosts is set
            if num_hosts_to_display:
                host_incident_counts = df_problems.groupby('host_name').size().reset_index(name='incident_count')
                sorted_primary_keys = host_incident_counts.sort_values(by='incident_count', ascending=False).head(num_hosts_to_display)['host_name'].tolist()
            else:
                sorted_primary_keys = sorted(df_problems['host_name'].unique().tolist())

            for primary_key in sorted_primary_keys:
                group_df = df_problems[df_problems['host_name'] == primary_key]
                incidents_list = []
                for _, row in group_df.sort_values(by='clock', ascending=False).iterrows():
                    incidents_list.append({
                        'name': row['name'],
                        'severity': row['severity_name'],
                        'clock': row['formatted_clock'],
                        'duration': row['formatted_duration'],
                        'acknowledges': row['processed_acknowledgements']
                    })
                grouped_data.append({
                    'primary_key_name': primary_key,
                    'incidents': incidents_list
                })

        elif primary_grouping == 'problem':
            # Group by problem name first
            problem_incident_counts = df_problems.groupby('name').size().reset_index(name='incident_count')
            sorted_primary_keys = problem_incident_counts.sort_values(by='incident_count', ascending=False)['name'].tolist()

            for primary_key in sorted_primary_keys:
                group_df = df_problems[df_problems['name'] == primary_key]
                # Then group by host within each problem
                hosts_affected = []
                for host_name, host_group_df in group_df.groupby('host_name'):
                    incidents_list = []
                    for _, row in host_group_df.sort_values(by='clock', ascending=False).iterrows():
                        incidents_list.append({
                            'name': row['name'], # Redundant but keeps structure consistent
                            'severity': row['severity_name'],
                            'clock': row['formatted_clock'],
                            'duration': row['formatted_duration'],
                            'acknowledges': row['processed_acknowledgements']
                        })
                    hosts_affected.append({
                        'host_name': host_name,
                        'incidents': incidents_list
                    })
                grouped_data.append({
                    'primary_key_name': primary_key,
                    'hosts_affected': sorted(hosts_affected, key=lambda x: x['host_name'])
                })

        data = {
            "grouped_data": grouped_data,
            "selected_severities": selected_severities_names,
            "show_duration": custom_options.get('show_duration', True),
            "show_acknowledgements": custom_options.get('show_acknowledgements', True),
            "primary_grouping": primary_grouping
        }
        return self.render("incidents", data)