# EdTech Revenue Growth Analytics

## Resumo executivo
Case sintético de Marketing Analytics e Revenue Analytics para uma EdTech digital de idiomas. O projeto conecta campanhas, creators, aulas gratuitas, CRM/WhatsApp, vendas, ativação, engajamento, retenção e expansão para apoiar decisões de investimento, corte, priorização comercial e governança de receita.

O foco não é apenas dashboard. O case mostra como uma liderança de Marketing, Growth, Comercial, CX, Produto, Engenharia e Dados poderia separar volume barato de receita qualificada, acompanhar meta versus realizado e transformar gaps em hipóteses, experimentos e plano de ação.

## Problema de negócio
Crescimento digital pode parecer saudável quando leads e CPL melhoram, mas esconder piora de CAC, baixa conversão, atraso comercial, ativação fraca ou receita de menor qualidade. A liderança precisa de uma visão única para decidir onde investir, onde cortar e quais hipóteses validar no próximo fechamento.

## Risco e oportunidade de receita
- Risco: escalar canais de alto volume que não convertem em matrícula ativada.
- Risco: comemorar receita acima da meta com CAC e payback deteriorando.
- Oportunidade: realocar verba para canais e segmentos com melhor LTV/CAC.
- Oportunidade: recuperar receita com CRM/WhatsApp e SLA P1.
- Oportunidade: usar aulas gratuitas e creators como alavancas assistidas, sem afirmar causalidade.

## Uso consultivo
O projeto usa linguagem responsável: "os dados sugerem", "há indícios", "hipótese provável", "precisa ser validado" e "a evidência disponível aponta para". Não há afirmação de causa raiz confirmada.

## O que o projeto entrega
- Dados sintéticos realistas de 210 dias.
- Pipeline Python para geração, scoring, fechamento mensal e relatórios.
- Base SQLite e arquivos CSV em `data/processed/`.
- Dashboard Streamlit com visão executiva e diagnósticos por funil, canal, campanha, segmento e produto.
- IA consultora rule-based, sem API externa.
- Consultor de gaps com evidências, hipóteses, validação e recomendações.
- Action Tracker com responsáveis, prioridade, impacto esperado e métrica de acompanhamento.
- Recomendações de experimentos com hipótese, métrica primária e critério mínimo de sucesso.
- Auditorias textual e especialista.
- Testes automatizados.

## Principais métricas
CAC, CPL, ROI, ROAS, LTV/CAC, payback, receita líquida, lead para matrícula, MQL rate, show-up rate, receita por participante, tempo de primeira resposta, ativação, engajamento, proxy de retenção, oportunidade de expansão e meta versus realizado.

## Fechamento mensal
O módulo `src/monthly_closing.py` gera:
- `performance_history.csv`
- `performance_targets.csv`
- `monthly_closing.csv`
- `variation_justifications.csv`

Ele calcula realizado contra meta, variação absoluta, variação percentual, variação contra mês anterior, status da meta, status do fechamento, principal driver provável e justificativa do analista.

## Camada de IA consultora
`src/ai_consultant.py` lê métricas, gaps, fechamento mensal, justificativas, plano de ação e experimentos. A saída fica em `docs/ai_consultant_analysis.md`.

A análise inclui:
- veredito executivo;
- principais achados;
- decisões recomendadas;
- gaps críticos;
- hipóteses e evidências ausentes;
- perguntas para liderança;
- plano de 30 dias;
- Action Plan Tracker;
- experimentos recomendados.

## Lógica de priorização de leads
`src/lead_scoring.py` aplica score rule-based de 0 a 100 usando intenção, engajamento, qualidade do canal, idioma, objetivo declarado, interação CRM, presença em aula, urgência de atendimento e conversão histórica por segmento.

Tiers:
- P1: score >= 80
- P2: score >= 60
- P3: score >= 40
- nurture: abaixo de 40

## Como rodar
```bash
python src/generate_data.py
python src/lead_scoring.py
python src/monthly_closing.py
python src/consultant_gap_finder.py
python src/action_tracker.py
python src/experiment_recommendations.py
python src/ai_consultant.py
python src/data_quality.py
python src/reports.py
python -m compileall src app
python -m pytest
python scripts/text_quality_audit.py
python scripts/specialist_audit.py
python scripts/run_streamlit_local.py
```

Dashboard local:
- padrão: [http://localhost:8501](http://localhost:8501)
- alternativa: defina `STREAMLIT_PORT` antes de rodar o launcher.

## Estrutura
```text
app/
src/
data/processed/
data/database/
docs/
tests/
scripts/
slides/
README.md
requirements.txt
```

## Aviso sobre dados e privacidade
Todos os dados são sintéticos. Não há dados pessoais reais, dados sensíveis ou APIs externas. IDs de lead, aluno, campanha e creator são fictícios.

Este projeto é apenas para portfólio, estudo e demonstração. Em produção, uma solução semelhante exigiria controles de LGPD e privacidade, incluindo consentimento, minimização, controle de acesso, mascaramento, retenção, auditoria, documentação de fontes e lineage básico.

## Limitações
- LTV é estimado e sintético.
- Atribuição creator-led é assistida, não causal.
- As recomendações são hipóteses de negócio e precisam de validação.
- Custos fixos, margem real por plano e cohorts longos não estão conectados a sistemas reais.

## Decisões recomendadas
1. Rebalancear investimento de canais de volume puro para canais com melhor LTV/CAC.
2. Implantar SLA P1 e roteamento de leads quentes antes de filas genéricas.
3. Otimizar show-up de aulas gratuitas antes de aumentar investimento em eventos.
4. Medir creators por receita assistida e aluno ativado, não apenas por leads.
5. Usar o fechamento mensal para separar crescimento saudável de crescimento comprado com piora de CAC.

## Stack técnica
Python, pandas, numpy, SQLite, Plotly, Streamlit e pytest.

## O que este case demonstra
Raciocínio executivo em Revenue Analytics, governança de receita, diagnóstico de funil, CRM/Sales Ops, qualidade de dados, ativação de produto, IA rule-based responsável e comunicação consultiva para liderança.
