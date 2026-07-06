# AGENTS.md

- Manter dados sintéticos.
- Não usar APIs externas.
- Não usar ML sem autorização.
- Manter IA rule-based.
- Não afirmar causa raiz.
- Preservar formatação PT-BR em textos e dashboard.
- Dashboard em português do Brasil.
- Identificadores técnicos em inglês, snake_case e ASCII.
- Análise deve ter padrão especialista de RevOps, Sales Ops, CRM Governance e Revenue Governance.
- Consultor deve apontar gaps com evidências, hipóteses, validação e recomendações.
- Não tratar CRM Data Quality como checklist técnico sem impacto em receita.
- Rodar `python src/generate_data.py`, `python src/consultant_gap_finder.py`, `python src/ai_consultant.py`, `python src/data_quality.py`, `python src/reports.py`, `python -m compileall src app` e `python -m pytest` antes de finalizar.
