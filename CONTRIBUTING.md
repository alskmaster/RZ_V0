Contribuindo
============

Padrão de mensagens de commit
-----------------------------

Siga o padrão abaixo para manter o histórico limpo e fácil de entender.

Formato:

  TIPO(ESCOPO): resumo curto em português

Tipos comuns:
- feat: nova funcionalidade
- fix: correção de bug
- docs: documentação
- style: estilo (sem alterar lógica)
- refactor: refatoração (sem mudar comportamento)
- perf: performance
- test: testes
- build: mudanças de build/deps
- ci: pipeline/CI
- chore: tarefas diversas
- revert: reverte commit

Exemplos:
- feat(mem): separar em módulos de tabela e gráficos
- fix(incidentes): corrigir abertura do modal de engrenagem
- docs: adicionar guia dos módulos de incidentes

Corpo (opcional):
- Explique o contexto, decisões e impactos.
- Inclua “Como testar” quando relevante.

Referências (opcional):
- Closes #123, Relates-to #456

Template de commit
------------------

Este repositório inclui um template em português: `.gitmessage_pt.txt`.

Para usar automaticamente no repositório, execute:

  git config commit.template .gitmessage_pt.txt

Após isso, o editor abrirá o template a cada `git commit`.

Boas práticas adicionais
------------------------
- Commits pequenos e focados, um assunto por vez.
- Mensagens claras, no imperativo: “adicionar”, “corrigir”, “refatorar”.
- Atualize documentação quando houver mudança de uso/fluxo.

