RZ_V0 — Guia Completo do Sistema, Onboarding e Fluxo de Módulos

Sumário
- Visão Geral
- Arquitetura
- Modelos de Dados (Banco)
- Fluxo de Geração de Relatórios (end-to-end)
- Integração Zabbix
- Coletores e Módulos (plugin system)
- Frontend: Builder de Relatório e “Engrenagens” (customização)
- Build, Execução e Ambiente
- Segurança e Observabilidade
- Onboarding (Usuário e Desenvolvedor)
- Roteiro: Criando um Novo Módulo
- Boas Práticas e Próximos Passos

Visão Geral
- Propósito: Sistema web para gerar relatórios PDF mensais a partir de métricas do Zabbix (SLA, CPU, Memória, Disco, Wi‑Fi, Incidentes, Inventário, etc.).
- Tecnologias: Flask, SQLAlchemy, Flask‑Login/CSRF, Pandas/Matplotlib, xhtml2pdf/PyPDF2.
- Conceito: Cada relatório é um conjunto de “módulos”. Cada módulo possui um coletor (backend) e um template (Jinja) e pode ter opções de customização via UI (“engrenagens”).

Arquitetura
- App Factory: app/__init__.py:42 cria a aplicação, configura extensões (db, login, csrf), registra blueprints e seeds básicos.
- Blueprints:
  - Auth: app/auth/routes.py:1 — login/logout.
  - Main: app/main/routes.py:1 — telas de geração, histórico e thread de geração.
  - Admin: app/admin/routes.py:1 — clientes, usuários, configurações e “metric keys”. Endpoints auxiliares: app/admin/metric_keys_api.py:1 e app/admin/debug_routes.py:1.
- Serviços e Orquestração:
  - ReportGenerator: app/services.py:88 — orquestra a coleta e montagem do PDF. Possui um “registry” COLLECTOR_MAP para instanciar coletores por tipo.
  - PDFBuilder: app/pdf_builder.py:1 — encapa, insere miolo HTML convertido em PDF e página final.
  - Zabbix API wrapper: app/zabbix_api.py:1 — requests JSON‑RPC com retry básico e utilidades (token, grupos, etc.).
- Camada de Coleta (Plugins):
  - BaseCollector: app/collectors/base_collector.py:1 — contrato para coletores; provê render(template, data) e _update_status.
  - RobustMetricEngine: app/collectors/robust_metric_engine.py:1 — engine resiliente de CPU/Mem/Disco, usando perfis, descoberta e fallback trends/history.
  - Coletores por módulo: app/collectors/*.py (cpu, mem, disk, latency/loss table+chart, incidents table+chart, kpi, sla, wifi, etc.).
- Templates: app/templates/
  - Layout base do app: app/templates/base.html:1 e app/templates/admin/base.html:1
  - “Miolo” do relatório: app/templates/_MIOLO_BASE.html
  - Templates por módulo: app/templates/modules/*.html
- Frontend/UI:
  - Builder de relatórios: app/templates/gerar_form.html:1 + app/static/js/gerar_form.js:1
  - Engrenagens por módulo: app/static/js/modules/*_gear.js

Modelos de Dados (Banco)
- Principais (app/models.py:1):
  - SystemConfig: branding, cores, logos, capas e rodapés de relatório.
  - Role, User: papéis (super_admin, admin, client), autenticação Flask‑Login.
  - Client: credenciais Zabbix por cliente, SLA de contrato e relação com grupos Zabbix (ClientZabbixGroup).
  - ClientZabbixGroup: vincula um cliente a group_ids do Zabbix.
  - Report: metadados de PDFs gerados (arquivo, mês de referência, autor, cliente).
  - ReportTemplate / ReportTemplateModule: estrutura para armazenar templates de layout; OBS: a view usa t.layout_json, o modelo atual não inclui este campo — avaliar ajuste.
  - MetricKeyProfile: cadastro dinâmico de chaves por tipo (cpu, memory, disk, wifi_clients), prioridade e cálculo (DIRECT/INVERSE).

Fluxo de Geração de Relatórios (end-to-end)
1) Usuário seleciona Cliente, Mês e adiciona Módulos (UI em gerar_form.html:1 / gerar_form.js:1).
2) POST /gerar_relatorio dispara uma thread (main/routes.py:33) com ReportGenerator.
3) ReportGenerator.generate (app/services.py:141):
   - Valida período (YYYY-MM -> timestamps mês inteiro).
   - Busca grupos do cliente e hosts (get_hosts).
   - Pré-coleta SLA se houver módulos dependentes (sla, kpi, top_hosts, etc.).
   - Para cada módulo do layout, instancia o coletor via COLLECTOR_MAP e chama collect().
   - Renderiza o miolo HTML (_MIOLO_BASE.html) com a junção dos módulos.
   - PDFBuilder combina capa -> miolo -> página final e salva o PDF (Report persistido).
4) A UI faz polling em /report_status/<task_id> até status “Concluído” e libera o download.

Integração Zabbix
- Login e Token: app/zabbix_api.py:34 obtém token via user.login com URL, usuário e senha do .env/config (Config).
- Requests: fazer_request_zabbix aplica retries e retorna result/error tratado.
- Acesso a dados:
  - Hosts: host.get (services.get_hosts): app/services.py#L365
  - Itens: item.get (services.get_items) com search/filter key_ e triggers opcionais: app/services.py#L408
  - Trends: trend.get (chunked): app/services.py#L439, get_trends_chunked: app/services.py#L458
  - Fallback: history.get agregado (min/avg/max): app/services.py#L505
  - Eventos/Problemas: event.get + problem.get para SLA e correlação: app/services.py (parte “Availability data”).

Coletores e Módulos (plugin system)
- Registry: app/services.py (COLLECTOR_MAP) mapeia string do tipo para classe do coletor.
- BaseCollector: obriga implemento de collect(all_hosts, period) e provê render(template, data).
- RobustMetricEngine:
  - Tenta perfis do banco (MetricKeyProfile), caso vazio faz “descoberta” de chaves comuns.
  - Usa trend.get e fallback para history.get, agregando min/avg/max.
  - Suporte a cálculo DIRECT/INVERSE e seleção do “melhor perfil por host” via prioridade.
- SLA e disponibilidade: ReportGenerator pré-coleta disponibilidade se houver módulos do conjunto {sla, sla_table, sla_chart, sla_plus, kpi, top_hosts, top_problems, stress}; problemas são correlacionados em janela do mês.
- Exemplos de coletores:
  - CPU: app/collectors/cpu_collector.py:1 (tabela + gráfico, usa RobustMetricEngine, fallback legado por perfis)
  - Disco: app/collectors/robust_metric_engine.py:126 (lógica para root/worst FS, filtros regex)
  - Incidentes: split em incidents_table e incidents_chart (docs/INCIDENTES.md)

Frontend: Builder de Relatório e “Engrenagens” (customização)
- Builder (gerar_form.js): monta um JSON layout [{ id, type, title, newPage, custom_options }]. Suporta arrastar e soltar, salvar/carregar templates, e customização por módulo via “engrenagens”.
- Engrenagens (customizadores): arquivos em app/static/js/modules/*_gear.js expõem window.ModuleCustomizers['module_type'] com métodos load/save (e modal Bootstrap). O builder detecta e aciona quando usuário clica no ícone da engrenagem do módulo.
- Exemplos: sla_chart_gear.js e sla_table_gear.js; opções como target_sla, top_n, order, highlight, etc. são injetadas em custom_options e consumidas no coletor/template.

Build, Execução e Ambiente
- Requisitos: Python 3.10+, wkhtmltoimage (opcional, via imgkit se usado por features), dependências de requirements.txt.
- Variáveis (.env):
  - SECRET_KEY, SUPERADMIN_PASSWORD (obrigatórias em produção).
  - DATABASE_URL (default sqlite:///zabbix_reporter_v20.db).
  - ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD (necessários para gerar relatórios).
  - PREFERRED_URL_SCHEME/DEBUG/LOG_LEVEL/UPLOAD_FOLDER/GENERATED_REPORTS_FOLDER.
- Rodar em desenvolvimento:
  - python -m venv .venv && .venv/Scripts/activate (Windows) ou source .venv/bin/activate
  - pip install -r requirements.txt
  - set FLASK_APP=run.py (Windows) ou export FLASK_APP=run.py
  - set DEBUG=1 e definir SECRET_KEY/SUPERADMIN_PASSWORD (mesmo em dev)
  - python run.py
- CLI útil: flask reset-superadmin --password "SuaSenha" (app/__init__.py:91)

Segurança e Observabilidade
- CSRF e sessão: Flask‑WTF habilitado globalmente; session cookies `HttpOnly`, `SameSite`, `Secure` quando https.
- Login: Flask‑Login, role‑based em utils.admin_required, redirects seguros, sem logar credenciais.
- Logs: request_id por requisição, before/after request com métricas e cabeçalhos de segurança (X‑Content‑Type‑Options, X‑Frame‑Options, X‑XSS‑Protection).
- Erros 400/403/404/500 tratados com logs e mensagens sintéticas.

Onboarding
- Para Usuário (Admin):
  1) Crie/valide o superadmin: FLASK_APP=run.py flask reset-superadmin --password "...".
  2) Faça login, acesse Admin > Clientes e cadastre o cliente com URL/usuário/senha do Zabbix; vincule grupos.
  3) Configure branding em Admin > Configurações (logos/cores/capa/rodapé).
  4) Em Admin > Gerenciador de Métricas: cadastre perfis (CPU/Mem/Disco/Wi‑Fi) ou use Descobrir (app/admin/metric_keys_api.py).
  5) Vá a “Gerar Relatório”, selecione Cliente e Mês, adicione módulos e personalize engrenagens quando disponível.
  6) Gere o relatório e acompanhe o status; baixe o PDF ao concluir.
- Para Desenvolvedor:
  1) Prepare o .env com SECRET_KEY, SUPERADMIN_PASSWORD, DATABASE_URL (opcional), ZABBIX_*.
  2) Crie venv, instale dependências e execute a app (ver seção “Build, Execução e Ambiente”).
  3) Leia app/services.py (COLLECTOR_MAP e ReportGenerator) e app/collectors/base_collector.py (contrato de plugins).
  4) Explore app/templates/modules e app/static/js/modules para ver padrões de template e engrenagem.
  5) Use /admin/debug_collect para diagnóstico de módulos CPU/MEM/DISK (contagem de itens/points).

Roteiro: Criando um Novo Módulo
1) Defina o tipo (string única) e objetivo do módulo. Ex.: "net_errors_chart".
2) Backend (coletor):
   - Crie app/collectors/net_errors_chart_collector.py herdando BaseCollector. Implemente collect(all_hosts, period, ...).
   - Use self.generator.get_items / get_trends_with_fallback / robust_aggregate conforme o tipo dos dados.
   - Retorne HTML via self.render('net_errors_chart', data_dict) usando um novo template Jinja em app/templates/modules/net_errors_chart.html.
   - Registre o coletor em app/services.py no COLLECTOR_MAP: {'net_errors_chart': NetErrorsChartCollector}.
3) Template (Jinja):
   - Siga padrões dos templates existentes em app/templates/modules; use classes Bootstrap, respeite new_page.
   - Para gráficos, gere o PNG base64 via app/charting.py (generate_chart ou generate_multi_bar_chart) no coletor e injete no template.
4) Engrenagem (opcional, recomendada):
   - Crie app/static/js/modules/net_errors_chart_gear.js expondo window.ModuleCustomizers['net_errors_chart'] com load/save e modal Bootstrap.
   - Inclua o novo script na página gerar_form (ex.: no final de app/templates/gerar_form.html, seguindo o padrão dos demais *_gear.js).
   - Defina e valide custom_options coerentes (e.g., top_n, order, filtros), aplicando‑as no coletor.
5) Disponibilização no Builder:
   - Garanta que o endpoint que lista módulos disponíveis inclua o seu tipo (o builder consulta URLS.get_modules — ver gerar_form.html/gerar_form.js e rota correspondente em main ou admin). Adicione o item { type: 'net_errors_chart', name: 'Erros de Rede (Gráfico)' }.
6) Testes manuais:
   - Use um cliente com grupos/hosts válidos.
   - Gere um relatório somente com o novo módulo; verifique status, HTML renderizado e PDF final.
   - Valide comportamento com e sem dados; mensagens amigáveis quando vazio.
7) Documente as opções no README ou docs/INCIDENTES.md‑style; adicione logs no coletor (_update_status) para depuração.

Boas Práticas e Próximos Passos
- Métricas (MetricKeyProfile):
  - Priorize a chave preferencial com prioridade baixa (1). Evite misturar DIRECT/INVERSE para o mesmo contexto.
  - Para Disco, use filtros (tmpfs/overlay/loop/snap) como em RobustMetricEngine.collect_disk_smart.
- Performance: prefira get_trends_chunked; use history.get agregado como fallback. Evite explosão de itens em uma única chamada.
- UX: forneça engrenagens com defaults sensatos; desabilite opções dependentes quando não aplicáveis.
- Observações/ajustes sugeridos:
  - Consistência ReportTemplate: alinhar modelo vs. uso de layout_json no template (ver app/templates/gerar_form.html: uso de t.layout_json).
  - Multi‑Zabbix por cliente (token/URL por cliente direto na engine) e cache de “perfil vencedor por host”.
  - UI de pré‑checagem de dados de módulo antes de gerar, para feedback rápido.

Apêndice — Referências Rápidas (arquivos)
- App factory: app/__init__.py:1
- Config: config.py:1
- Execução: run.py:1
- Serviços: app/services.py:1
- Zabbix API: app/zabbix_api.py:1
- Modelos: app/models.py:1
- Coletores: app/collectors/*.py; contrato: app/collectors/base_collector.py:1
- Builder: app/templates/gerar_form.html:1 e app/static/js/gerar_form.js:1
- Engrenagens: app/static/js/modules/*_gear.js
- Templates de módulos: app/templates/modules/*.html

