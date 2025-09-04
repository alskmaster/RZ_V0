from .base_collector import BaseCollector
from flask import current_app
import datetime as dt
import pandas as pd


class ResiliencePanelCollector(BaseCollector):
    """
    Painel de Resiliência (SLA Preciso) — Host-based

    - Respeita seleção de Cliente e Mês (usa all_hosts e period recebidos do ReportGenerator).
    - Calcula SLA por host reutilizando a infraestrutura existente de disponibilidade
      (correlação de eventos de PING) e a meta do cliente (sem entrada manual).
    - Oferece apenas o filtro "Host (contém)" e subperíodo opcional.

    custom_options suportadas:
      - host_name_contains: substring para filtrar o nome visível do host
      - period_sub_filter: full_month | last_24h | last_7d (default: full_month)
    """

    def _fmt_seconds(self, total_seconds):
        try:
            total_seconds = int(total_seconds or 0)
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            return "00:00:00"

    def _apply_period_subfilter(self, period, sub):
        start, end = period['start'], period['end']
        try:
            now = int(dt.datetime.now().timestamp())
        except Exception:
            from time import time as _t
            now = int(_t())
        if sub == 'last_24h':
            end = now
            start = end - 24 * 3600
        elif sub == 'last_7d':
            end = now
            start = end - 7 * 24 * 3600
        return {'start': int(start), 'end': int(end)}

    def collect(self, all_hosts, period):
        opts = self.module_config.get('custom_options', {}) or {}
        host_contains = (opts.get('host_name_contains') or '').strip()
        decimals = int(opts.get('decimals') or 2)
        highlight = (opts.get('highlight_below_goal') is not False)
        period = self._apply_period_subfilter(period, opts.get('period_sub_filter', 'full_month'))
        try:
            _s = dt.datetime.fromtimestamp(int(period['start'])).strftime('%d-%m-%Y')
            _e = dt.datetime.fromtimestamp(int(period['end'])).strftime('%d-%m-%Y')
            self._update_status(f"resilience_panel | período efetivo {_s} – {_e}")
        except Exception:
            pass

        # SLA alvo do cliente (sem entrada manual)
        try:
            target_sla = self.generator._get_client_sla_contract()
        except Exception:
            target_sla = None

        # Filtra hosts por "contém" (se informado)
        if host_contains:
            try:
                all_hosts = [h for h in (all_hosts or []) if host_contains.lower() in str(h.get('nome_visivel','')).lower()]
            except Exception:
                pass
        if not all_hosts:
            return self.render('resilience_panel', {
                'rows': [],
                'target_sla': target_sla,
                'period': period,
                'error': 'Nenhum host para calcular disponibilidade.'
            })

        self._update_status("Calculando disponibilidade por host (SLA)...")
        try:
            data, err = self.generator._collect_availability_data(all_hosts, period, target_sla)
        except Exception:
            current_app.logger.exception('[ResiliencePanel] Falha no cálculo de disponibilidade')
            data, err = None, 'Falha ao calcular disponibilidade.'

        if err or not data or 'df_sla_problems' not in data:
            return self.render('resilience_panel', {
                'rows': [],
                'target_sla': target_sla,
                'period': period,
                'error': err or 'Não foi possível obter dados de SLA.'
            })

        df = data['df_sla_problems']
        rows = []
        if isinstance(df, pd.DataFrame) and not df.empty:
            for _, r in df.sort_values(by='SLA (%)', ascending=True).iterrows():
                sla_val = None
                try:
                    sla_val = float(r.get('SLA (%)'))
                except Exception:
                    sla_val = None
                dsecs = int(r.get('Downtime (s)') or 0)
                rows.append({
                    'host': r.get('Host'),
                    'sla': sla_val,
                    'sla_str': (f"{sla_val:.{decimals}f}" if sla_val is not None else None),
                    'downtime': dsecs,
                    'downtime_hms': self._fmt_seconds(dsecs),
                })

        # Resumo criativo
        summary_text = None
        try:
            total = len(rows)
            below = 0
            if target_sla is not None:
                below = sum(1 for r in rows if (r['sla'] is not None and r['sla'] < float(target_sla)))
                ok = total - below
                summary_text = (
                    f"No período analisado, avaliamos {total} host(s). "
                    f"{ok} dentro da meta e {below} abaixo de {float(target_sla):.{decimals}f}% de SLA."
                )
            else:
                # Sem meta definida no cliente
                avg = None
                try:
                    vals = [r['sla'] for r in rows if r['sla'] is not None]
                    if vals:
                        avg = sum(vals)/len(vals)
                except Exception:
                    avg = None
                summary_text = (
                    f"No período analisado, avaliamos {total} host(s). "
                    + (f"Média de SLA: {avg:.{decimals}f}%" if avg is not None else "")
                )
        except Exception:
            summary_text = None

        return self.render('resilience_panel', {
            'rows': rows,
            'target_sla': target_sla,
            'period': period,
            'summary_text': summary_text,
            'highlight_below_goal': bool(highlight),
        })
