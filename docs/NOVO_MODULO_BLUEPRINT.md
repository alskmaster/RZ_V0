Blueprint: Criando um Novo Módulo (Collector + Template + UI)

Objetivo
- Servir como guia prático e repetível para adicionar um módulo ao sistema (coletor backend + template Jinja + engrenagem de customização + registro no builder).

Checklist Rápido
- [ ] Criar coletor em app/collectors/<module>_collector.py
- [ ] Adicionar entrada no COLLECTOR_MAP (app/services.py)
- [ ] Criar template Jinja em app/templates/modules/<module>.html
- [ ] (Opcional) Criar engrenagem em app/static/js/modules/<module>_gear.js e incluir no gerar_form.html
- [ ] Expor no endpoint de módulos disponíveis para o builder (label e type)
- [ ] Testar geração isolada e com outras seções

Exemplo: net_errors_chart

1) Coletor (backend)
Arquivo: app/collectors/net_errors_chart_collector.py

from .base_collector import BaseCollector
from flask import current_app
import pandas as pd

class NetErrorsChartCollector(BaseCollector):
    def collect(self, all_hosts, period):
        self._update_status("Coletando erros de rede...")

        # 1) Descobrir itens (exemplo com key_ fictícia; ajuste conforme Zabbix)
        host_ids = [h['hostid'] for h in all_hosts]
        items = self.generator.get_items(host_ids, 'net.if.in.errors', search_by_key=True)
        if not items:
            return "<p><i>Nenhum item de erros de rede encontrado para os hosts selecionados.</i></p>"

        # 2) Trends com fallback/robustez (value_type 3 = float; ajustar conforme item)
        item_ids = [i['itemid'] for i in items]
        trends = self.generator.get_trends_with_fallback(item_ids, period['start'], period['end'], history_value_type=3)
        if not trends:
            return "<p><i>Sem dados de tendências para erros de rede no período.</i></p>"

        # 3) Agregar e preparar dados para o gráfico
        df = pd.DataFrame(trends)
        df[['value_avg']] = df[['value_avg']].astype(float)
        # média por hostid
        host_map = {h['hostid']: h['nome_visivel'] for h in all_hosts}
        item_to_host = {str(i['itemid']): i['hostid'] for i in items}
        df['itemid'] = df['itemid'].astype(str)
        df['hostid'] = df['itemid'].map(item_to_host)
        df = df.groupby('hostid')['value_avg'].mean().reset_index()
        df['Host'] = df['hostid'].map(host_map)
        df.rename(columns={'value_avg': 'Avg'}, inplace=True)
        df = df[['Host', 'Avg']]

        # 4) Renderizar template
        data = { 'serie': df.to_dict('records') }
        return self.render('net_errors_chart', data)

2) Registro no COLLECTOR_MAP
Arquivo: app/services.py (procure por COLLECTOR_MAP)

COLLECTOR_MAP = {
    # ... existentes ...
    'net_errors_chart': NetErrorsChartCollector,
}

3) Template Jinja
Arquivo: app/templates/modules/net_errors_chart.html

<section class="mb-4">
  {% if new_page %}<div style="page-break-before: always;"></div>{% endif %}
  <h3>{{ title or 'Erros de Rede (média)' }}</h3>
  {% if data.serie and data.serie|length > 0 %}
    <table class="table table-sm">
      <thead><tr><th>Host</th><th>Média</th></tr></thead>
      <tbody>
        {% for row in data.serie %}
          <tr><td>{{ row.Host }}</td><td>{{ '%.2f'|format(row.Avg) }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p><i>Sem dados para exibir.</i></p>
  {% endif %}
  <small class="text-muted">Período: mês de referência do relatório.</small>
  {% if system_config and system_config.footer_text %}
    <div class="mt-2"><small>{{ system_config.footer_text }}</small></div>
  {% endif %}
</section>

4) Engrenagem de customização (opcional)
Arquivo: app/static/js/modules/net_errors_chart_gear.js

(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};
  window.ModuleCustomizers['net_errors_chart'] = {
    // Exemplo simples sem modal: apenas guarda opções no objeto
    load: function(opts) { this._opts = opts || {}; },
    save: function() { return this._opts || {}; }
  };
})();

Inclua o script no gerar_form.html junto dos demais *_gear.js.

5) Expor no Builder
- O builder obtém a lista de módulos via endpoint (ver gerar_form.js/URLS.get_modules). Adicione um item:

{
  "type": "net_errors_chart",
  "name": "Erros de Rede (Gráfico)"
}

6) Testes
- Gere relatório com apenas o novo módulo.
- Valide path feliz (dados presentes) e vazio (mensagem amigável).
- Verifique PDF final (capa, miolo, página final) e histórico.

Notas
- Ajuste value_type de history.get conforme o tipo do item no Zabbix.
- Utilize RobustMetricEngine quando fizer sentido (CPU/Mem/Disco) para priorização por host e fallback automático.
- Use self._update_status(...) para logs de progresso visíveis na UI.

