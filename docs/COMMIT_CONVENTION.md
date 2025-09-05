Padrão de Mensagens de Commit

Formato obrigatório (cabeçalho):
[Ação] [Serviço] [Sessão] - Descrição concisa da atualização

Diretrizes
- Ação: Ajuste | Fix | Refatoração | Doc | Feat | Chore (ou similar, em PT‑BR)
- Serviço: área do sistema (WebApp, Backend, Builder, Admin, Zabbix, Repo, etc.)
- Sessão: contexto específico (Geração, UI, Resiliência, PDF, Auth, etc.)
- Descrição: curta, no imperativo (“Corrige…”, “Adiciona…”, “Atualiza…”)
- Corpo (opcional): detalhar motivação, impacto, tickets e breaking changes.

Exemplos
- [Ajuste] [WebApp] [UI] - Corrige labels com acentuação no builder
- [Feat] [Backend] [SLA] - Adiciona cálculo de SLA por serviço
- [Doc] [Repo] [Contrib] - Documenta padrão de commits e hooks

Template
O repositório inclui o arquivo .gitmessage.txt e está configurado para abrir esse template ao executar git commit, facilitando o preenchimento no padrão.

Validação automática (hook)
Opcionalmente, usamos um hook de commit para validar o padrão. Se necessário, desative momentaneamente com --no-verify (não recomendado).

