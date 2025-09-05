Blueprint: Criando um Novo Modulo (Collector + Template + UI)

Objetivo
- Servir como guia prÃƒÂ¡tico e repetÃƒÂ­vel para adicionar um mÃƒÂ³dulo ao sistema (coletor backend + template Jinja + engrenagem de customizaÃƒÂ§ÃƒÂ£o + registro no builder).

Checklist RÃƒÂ¡pido
- [ ] Criar coletor em app/collectors/<module>_collector.py
- [ ] Adicionar entrada no COLLECTOR_MAP (app/services.py)
- [ ] Criar template Jinja em app/templates/modules/<module>.html
- [ ] Criar engrenagem em app/static/js/modules/<module>_gear.js e incluir no gerar_form.html
- [ ] Criar na engrenagem funÃƒÂ§ÃƒÂµes de customizaÃƒÂ§ÃƒÂ£o padrÃƒÂ£o em todos os modulos: 
		Filtros:
			Host (contÃƒÂ©m):
			Excluir Hosts (contÃƒÂ©m): Lista separada por virgula
			Ordenar por: Hosts, outras opÃƒÂ§ÃƒÂµes do mÃƒÂ³dulo
			TÃƒÂ­tulo do mÃƒÂ³dulo:
			Outras opÃƒÂ§ÃƒÂµes de sua sugestÃƒÂ£o, mÃƒÂ­nimo 4 outras.
- [ ] Expor no endpoint de mÃƒÂ³dulos disponÃƒÂ­veis para o builder (label e type)
- [ ] Testar geraÃƒÂ§ÃƒÂ£o isolada e com outras seÃƒÂ§ÃƒÂµes
- 

Exemplo: net_errors_chart

1) Coletor (backend)
Arquivo: app/collectors/net_errors_chart_collector.py

from .base_collector import BaseCollector
from flask import current_app
import pandas as pd

class NetErrorsChartCollector(BaseCollector):
    def collect(self, all_hosts, period):
        self._update_status("Coletando erros de rede...")

        # 1) Descobrir itens (exemplo com key_ fictÃƒÂ­cia; ajuste conforme Zabbix)
        host_ids = [h['hostid'] for h in all_hosts]
        items = self.generator.get_items(host_ids, 'net.if.in.errors', search_by_key=True)
        if not items:
            return "<p><i>Nenhum item de erros de rede encontrado para os hosts selecionados.</i></p>"

        # 2) Trends com fallback/robustez (value_type 3 = float; ajustar conforme item)
        item_ids = [i['itemid'] for i in items]
        trends = self.generator.get_trends_with_fallback(item_ids, period['start'], period['end'], history_value_type=3)
        if not trends:
            return "<p><i>Sem dados de tendÃƒÂªncias para erros de rede no perÃƒÂ­odo.</i></p>"

        # 3) Agregar e preparar dados para o grÃƒÂ¡fico
        df = pd.DataFrame(trends)
        df[['value_avg']] = df[['value_avg']].astype(float)
        # mÃƒÂ©dia por hostid
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
  <h3>{{ title or 'Erros de Rede (mÃƒÂ©dia)' }}</h3>
  {% if data.serie and data.serie|length > 0 %}
    <table class="table table-sm">
      <thead><tr><th>Host</th><th>MÃƒÂ©dia</th></tr></thead>
      <tbody>
        {% for row in data.serie %}
          <tr><td>{{ row.Host }}</td><td>{{ '%.2f'|format(row.Avg) }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p><i>Sem dados para exibir.</i></p>
  {% endif %}
  <small class="text-muted">PerÃƒÂ­odo: mÃƒÂªs de referÃƒÂªncia do relatÃƒÂ³rio.</small>
  {% if system_config and system_config.footer_text %}
    <div class="mt-2"><small>{{ system_config.footer_text }}</small></div>
  {% endif %}
</section>

4) Engrenagem de customizaÃƒÂ§ÃƒÂ£o (opcional)
Arquivo: app/static/js/modules/net_errors_chart_gear.js

(function(){
  window.ModuleCustomizers = window.ModuleCustomizers || {};
  window.ModuleCustomizers['net_errors_chart'] = {
    // Exemplo simples sem modal: apenas guarda opÃƒÂ§ÃƒÂµes no objeto
    load: function(opts) { this._opts = opts || {}; },
    save: function() { return this._opts || {}; }
  };
})();

Inclua o script no gerar_form.html junto dos demais *_gear.js.

5) Expor no Builder
- O builder obtÃƒÂ©m a lista de mÃƒÂ³dulos via endpoint (ver gerar_form.js/URLS.get_modules). Adicione um item:

{
  "type": "net_errors_chart",
  "name": "Erros de Rede (GrÃƒÂ¡fico)"
}

6) Testes
- Gere relatÃƒÂ³rio com apenas o novo mÃƒÂ³dulo.
- Valide path feliz (dados presentes) e vazio (mensagem amigÃƒÂ¡vel).
- Verifique PDF final (capa, miolo, pÃƒÂ¡gina final) e histÃƒÂ³rico.

Notas
- Ajuste value_type de history.get conforme o tipo do item no Zabbix.
- Utilize RobustMetricEngine quando fizer sentido (CPU/Mem/Disco) para priorizaÃƒÂ§ÃƒÂ£o por host e fallback automÃƒÂ¡tico.
- Use self._update_status(...) para logs de progresso visÃƒÂ­veis na UI.


Padrao de Nomes e Codificacao (obrigatorio)
- Em codigo Python e JSON de APIs: use nomes ASCII (sem acentos) para evitar erros de source-encoding e garantir estabilidade cross-platform.
- Em templates HTML/Jinja: se precisar de acentos, mantenha o arquivo em UTF-8 e confirme <meta charset="UTF-8">.
- Endpoint get_available_modules: os name retornados sao normalizados para ASCII automaticamente. Ainda assim, prefira cadastrar nomes ja em ASCII.
- Validacao ao criar novo modulo:
  - [ ] Rodar o app e abrir "Gerar Relatorio": checar se todos os nomes de modulos aparecem legiveis (sem caracteres quebrados).
  - [ ] Conferir logs que nao ha SyntaxError por bytes nao-UTF8.
  - [ ] Se necessario, substituir nomes por ASCII no backend e usar acentos apenas na renderizacao final (templates/PDF).