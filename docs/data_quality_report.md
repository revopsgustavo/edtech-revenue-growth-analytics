# Textura de Qualidade de Dados

A análise trata qualidade como risco de receita, não como checklist técnico.

- required_fields em campaigns.csv: pass (0). Impacto: Campos ausentes reduzem confiança em CAC, receita e fechamento.
- required_nulls em campaigns.csv: pass (0). Impacto: Nulos podem afetar roteamento, metas e atribuição.
- required_fields em daily_marketing_spend.csv: pass (0). Impacto: Campos ausentes reduzem confiança em CAC, receita e fechamento.
- required_nulls em daily_marketing_spend.csv: pass (0). Impacto: Nulos podem afetar roteamento, metas e atribuição.
- required_fields em leads.csv: pass (0). Impacto: Campos ausentes reduzem confiança em CAC, receita e fechamento.
- required_nulls em leads.csv: warn (190). Impacto: Nulos podem afetar roteamento, metas e atribuição.
- required_fields em funnel_events.csv: pass (0). Impacto: Campos ausentes reduzem confiança em CAC, receita e fechamento.
- required_nulls em funnel_events.csv: pass (0). Impacto: Nulos podem afetar roteamento, metas e atribuição.
- required_fields em enrollments.csv: pass (0). Impacto: Campos ausentes reduzem confiança em CAC, receita e fechamento.
- required_nulls em enrollments.csv: pass (0). Impacto: Nulos podem afetar roteamento, metas e atribuição.
- required_fields em performance_targets.csv: pass (0). Impacto: Campos ausentes reduzem confiança em CAC, receita e fechamento.
- required_nulls em performance_targets.csv: pass (0). Impacto: Nulos podem afetar roteamento, metas e atribuição.
- required_fields em monthly_closing.csv: pass (0). Impacto: Campos ausentes reduzem confiança em CAC, receita e fechamento.
- required_nulls em monthly_closing.csv: pass (0). Impacto: Nulos podem afetar roteamento, metas e atribuição.
- required_fields em variation_justifications.csv: pass (0). Impacto: Campos ausentes reduzem confiança em CAC, receita e fechamento.
- required_nulls em variation_justifications.csv: pass (0). Impacto: Nulos podem afetar roteamento, metas e atribuição.
- leads_without_campaign em leads.csv: pass (0). Impacto: Afeta ROI e atribuição.
- leads_without_owner em leads.csv: warn (190). Impacto: Pode gerar perda de receita por SLA.
- inconsistent_funnel em funnel_events.csv: pass (0). Impacto: Quebra leitura de conversão.
- enrollment_without_lead em enrollments.csv: pass (0). Impacto: Afeta CAC e origem de receita.
- spend_without_campaign_id em daily_marketing_spend.csv: pass (0). Impacto: Afeta ROAS.
- negative_values em all: pass (0). Impacto: Pode distorcer métricas financeiras.
- duplicates em core_ids: pass (0). Impacto: Afeta contagem executiva.
- missing_targets em performance_targets.csv: pass (0). Impacto: Sem metas não há governança de performance.
- monthly_closing_without_month em monthly_closing.csv: pass (0). Impacto: Bloqueia fechamento.
- variation_without_actual em variation_justifications.csv: pass (0). Impacto: Enfraquece justificativa.
- justification_without_metric em variation_justifications.csv: pass (0). Impacto: Dificulta decisão.