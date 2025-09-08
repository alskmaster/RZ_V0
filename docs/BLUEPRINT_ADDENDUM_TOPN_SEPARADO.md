Atualizacao: Top N separado (Tabela x Grafico)

Contexto
- Para manter consistencia e flexibilidade, novos modulos devem aceitar limites de Top N separados para a tabela e para o grafico.
- Isto evita obrigar a mesma quantidade de dados em ambas as visualizacoes.

Requisito
- Em custom_options do modulo, suportar:
  - top_n_table: inteiro (linhas exibidas na tabela)
  - top_n_chart: inteiro (series/linhas usadas no grafico)
  - top_n: inteiro opcional de compatibilidade (fallback quando um dos campos acima nao for informado)
- Comportamento esperado no coletor:
  1) Aplicar filtros/ordenacao normalmente.
  2) Gerar dois subconjuntos ja ordenados:
     - dados_tabela = dados.head(top_n_table)
     - dados_grafico = dados.head(top_n_chart)
  3) Respeitar show_chart: so gerar chart_b64 quando show_chart=true e houver dados suficientes.

Snippet (fallbacks) no coletor

    o = self.module_config.get('custom_options', {}) or {}
    top_n_common = int(o.get('top_n') or 5)
    top_n_table = int(o.get('top_n_table') or top_n_common)
    top_n_chart = int(o.get('top_n_chart') or top_n_common)

UI (engrenagem *_gear.js)
- Expor dois inputs numericos: "Top N (Tabela)" e "Top N (Grafico)".
- No save(), persistir { top_n_table, top_n_chart } e (opcionalmente) top_n para compatibilidade.

