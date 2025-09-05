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
Requisitos minimos (baseados no Painel de Resiliencia — SLA Preciso)
- Objetivo: padronizar o que cada novo modulo deve aceitar/entregar para manter consistencia na UI, no builder e no PDF.
- Escopo: aplique estes requisitos quando fizer sentido ao seu modulo. Nao altere modulos existentes ao adotar este padrao.

- custom_options obrigatorias (quando aplicavel):
  - host_name_contains: substring para filtrar o nome visivel do host.
  - exclude_hosts_contains: lista separada por virgulas para excluir hosts por substring.
  - period_sub_filter: 'full_month' | 'last_24h' | 'last_7d' (default: 'full_month').
  - decimals: inteiro para formatacao numerica (ex.: casas decimais de SLA ou metricas similares).
  - sort_by: chave de ordenacao primaria; sugerido: 'sla' | 'downtime' | 'host' (ou chaves coerentes ao seu modulo).
  - sort_asc: boolean; true para ordem ascendente.
  - top_n: inteiro opcional limitando a N linhas/series apos a ordenacao.
  - show_chart: boolean; se true, o coletor deve produzir imagem base64 do grafico quando aplicavel.
  - chart_color: cor base do grafico (hex RGB, ex.: '#4e79a7').
  - below_color: cor para destacar valores abaixo de meta/objetivo (quando aplicavel).
  - x_axis_0_100: boolean; fixa eixo X de 0 a 100 (quando a escala for percentual).

- Titulo do modulo:
  - Respeite o campo 'title' no modulo. A engrenagem pode salvar internamente como '__title' e o builder propagar para 'title'.
  - Em graficos, utilize 'title' como titulo do chart quando fizer sentido.

- Comportamento do coletor (BaseCollector.collect):
  - Assinatura: collect(all_hosts, period) e leitura de self.module_config.get('custom_options', {}).
  - Aplique filtros host_name_contains e exclude_hosts_contains antes de qualquer chamada pesada.
  - Implemente period_sub_filter ajustando o periodo efetivo (full_month/last_24h/last_7d).
  - Utilize self._update_status(...) para logs perceptiveis na UI (inicio, filtros aplicados, etapas relevantes).
  - Seja resiliente: retorne render(template, { 'error': 'Mensagem amigavel' }) quando nao houver dados.
  - Aplique ordenacao/sort_by e sort_asc; depois, se definido, aplique top_n.
  - So gere grafico (show_chart) quando houver dados suficientes; retorne 'chart_b64' com PNG em base64.
  - Nunca assuma que metas/contratos existem; quando aplicavel, obtenha meta via self.generator._get_client_sla_contract() e trate None.

- Template (Jinja):
  - Estrutura sugerida: titulo H2/H3, alerta para erros/sem dados, tabela responsiva (Bootstrap) e grafico opcional.
  - Campos comuns (quando aplicavel):
    - rows: lista de objetos coerentes ao modulo (ex.: { host, sla, sla_str, downtime_hms }).
    - target_sla: meta/objetivo (quando existir); use para destaque condicional.
    - summary_text: frase curta resumindo achados (ex.: "N hosts, X ok, Y abaixo da meta").
    - chart_b64: imagem em base64 do grafico (quando show_chart=true).
    - highlight_below_goal: boolean para aplicar classe/style de destaque em linhas abaixo da meta.
    - period: periodo efetivo considerado (start/end epoch ints) para referencia/debug.

- Registro e disponibilizacao:
  - Registre no COLLECTOR_MAP (app/services.py) com chave 'type' em ASCII: ex.: 'resilience_panel'.
  - Exponha no endpoint de modulos (app/main/routes.py:get_available_modules): { type, name }.
  - Crie engrenagem em app/static/js/modules/<type>_gear.js com load/save, modal Bootstrap e defaults coerentes.
  - Inclua a engrenagem no template app/templates/gerar_form.html junto aos demais *_gear.js.

- Codificacao e nomes (reforce):
  - Em Python/JSON: use apenas ASCII em identificadores e strings de controle para evitar problemas de encoding.
  - Em HTML/Jinja: se precisar de acentos, confirme que o arquivo esta em UTF-8 e inclua <meta charset="UTF-8"> quando aplicavel.

- Validacao rapida antes de abrir PR:
  - [ ] UI lista o novo modulo em "Adicionar Modulo" com name legivel.
  - [ ] Engrenagem abre, salva e repassa custom_options ao coletor.
  - [ ] Coletor aplica filtros/periodo/ordenacao/top_n corretamente.
  - [ ] Sem dados: template exibe mensagem amigavel; com dados: tabela/grafico coerentes.
  - [ ] PDF final gera sem erros; logs (_update_status) aparecem com textos claros.
