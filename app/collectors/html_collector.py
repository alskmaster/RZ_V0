from .base_collector import BaseCollector
import re
import datetime as dt


class HtmlCollector(BaseCollector):
    """
    Módulo Texto/HTML Customizado (novo padrão):
    - Usa module_config['custom_options'] para obter conteúdo e opções
    - Suporta placeholders simples ({{client.name}}, {{client.sla}}, {{period.ref}}, {{date.today}})
    - Faz sanitização básica do HTML antes de renderizar
    """

    def _sanitize_html(self, html: str) -> str:
        if not html:
            return ''
        # Remove comentários
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove tags potencialmente perigosas e seu conteúdo
        for tag in ("script", "style", "iframe", "object", "embed"):
            html = re.sub(rf"<\s*{tag}[^>]*>.*?<\s*/\s*{tag}\s*>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove atributos on* (onclick, onload, ...)
        html = re.sub(r"\s+on[a-z]+\s*=\s*\"[^\"]*\"", "", html, flags=re.IGNORECASE)
        html = re.sub(r"\s+on[a-z]+\s*=\s*'[^']*'", "", html, flags=re.IGNORECASE)
        html = re.sub(r"\s+on[a-z]+\s*=\s*[^\s>]+", "", html, flags=re.IGNORECASE)
        # Neutraliza javascript: em href/src
        html = re.sub(r"(href|src)\s*=\s*\"javascript:[^\"]*\"", r"\1=\"#\"", html, flags=re.IGNORECASE)
        html = re.sub(r"(href|src)\s*=\s*'javascript:[^']*'", r"\1='#'", html, flags=re.IGNORECASE)
        return html

    def _apply_placeholders(self, html: str, period: dict) -> str:
        try:
            client = self.generator.client
        except Exception:
            client = None

        try:
            start = dt.datetime.fromtimestamp(period.get('start')) if isinstance(period, dict) else None
            ref_label = start.strftime('%B de %Y').capitalize() if start else ''
        except Exception:
            ref_label = ''

        # Extras
        system = getattr(self.generator, 'system_config', None)
        company = getattr(system, 'company_name', '') if system else ''
        try:
            end = dt.datetime.fromtimestamp(period.get('end')) if isinstance(period, dict) else None
            start_str = start.strftime('%d/%m/%Y') if start else ''
            end_str = end.strftime('%d/%m/%Y') if end else ''
            ref_short = start.strftime('%m/%Y') if start else ''
        except Exception:
            start_str = end_str = ref_short = ''

        # Hosts count if available
        try:
            hosts_count = len(self.generator.cached_data.get('all_hosts', []))
        except Exception:
            hosts_count = ''

        mapping = {
            '{{client.name}}': (client.name if getattr(client, 'name', None) else ''),
            '{{client.sla}}': (str(getattr(client, 'sla_contract', '')) if client else ''),
            '{{period.ref}}': ref_label,
            '{{date.today}}': dt.datetime.now().strftime('%d/%m/%Y'),
            '{{client.id}}': (str(getattr(client, 'id', '')) if client else ''),
            '{{system.company}}': company,
            '{{period.start}}': start_str,
            '{{period.end}}': end_str,
            '{{period.ref_short}}': ref_short,
            '{{hosts.count}}': str(hosts_count),
        }
        out = html or ''
        for k, v in mapping.items():
            out = out.replace(k, v)
        return out

    def collect(self, all_hosts, period):
        self._update_status("Processando Texto/HTML customizado...")

        opts = self.module_config.get('custom_options') or {}
        raw_html = opts.get('content', '')
        align = (opts.get('text_align') or 'left').lower()
        if align not in {'left', 'center', 'right', 'justify'}:
            align = 'left'

        # Placeholders e sanitização
        with_vars = self._apply_placeholders(raw_html, period)
        safe_html = self._sanitize_html(with_vars)

        # Empacota com alinhamento opcional
        if align and align != 'left':
            safe_html = f'<div style="text-align:{align};">{safe_html}</div>'

        # Estilo de caixa opcional
        style = (opts.get('box_style') or 'none').lower()
        style_map = {
            'none': '',
            'note': 'callout callout-note',
            'info': 'callout callout-info',
            'success': 'callout callout-success',
            'warning': 'callout callout-warning',
            'danger': 'callout callout-danger',
        }
        box_class = style_map.get(style, '')

        module_data = {'content': safe_html, 'text_align': align, 'box_class': box_class}
        return self.render('custom_html', module_data)
