import pandas as pd
try:
    from .utils import read_csv, save_csv, DOCS, safe_div
    from .metrics import summarize_channel_performance
except ImportError:
    from utils import read_csv, save_csv, DOCS, safe_div
    from metrics import summarize_channel_performance


def gap(gap_id, area, metric, current, expected, severity, evidence, hypothesis, missing, question, action, owner, urgency, impact, follow):
    return {
        "gap_id": gap_id,
        "area": area,
        "metric": metric,
        "current_value": current,
        "expected_value": expected,
        "severity": severity,
        "evidence": evidence,
        "likely_hypothesis": hypothesis,
        "missing_evidence": missing,
        "validation_question": question,
        "recommended_action": action,
        "owner": owner,
        "urgency": urgency,
        "expected_impact": impact,
        "follow_up_metric": follow,
        "status": "open",
    }


def classify_gap(row):
    area = str(row.get("area", "")).lower()
    metric = str(row.get("metric", "")).lower()
    evidence = str(row.get("evidence", "")).lower()
    text = f"{area} {metric} {evidence}"
    if "data" in text or "incomplet" in text or "tracking" in text:
        return "Data / Tracking", "data_quality", "Data Engineering / Analytics", "Data Lead"
    if "p1 sla" in text or "resposta" in text:
        return "Sales Ops", "sales_sla", "SDR Team", "Líder de Sales Ops"
    if "leads vs enrollments" in text or "conversion" in text or "matrícula" in text:
        return "Sales", "funnel_conversion", "Sales / SDR Team", "Head Comercial"
    if "free class" in text or "show-up" in text or "presença" in text or "evento" in text:
        return "Organic / Content", "event_attendance", "Content / Events", "Líder de Growth"
    if "activation" in text or "onboarding" in text:
        return "Product", "activation_gap", "Product / CX", "Head de Produto ou Head de CX"
    if "revenue vs cac" in text or "margem" in text:
        return "Finance / Revenue + Paid Media", "margin_pressure", "Revenue / Growth", "Head de Growth ou Finance Partner"
    if "crm" in text:
        return "CRM / Lifecycle", "crm_reactivation", "CRM / Lifecycle", "Gerente de CRM"
    if "creator" in text or "influencer" in text:
        return "Creator / Influencer", "content_performance", "Creator / Influencer", "Líder de Growth"
    if "cac" in text or "cpl" in text or "ltv/cac" in text:
        return "Paid Media", "acquisition_efficiency", "Growth / Paid Media", "Head de Marketing ou Líder de Growth"
    return "Mixed / Cross-functional", "mixed_driver", "Marketing + Sales + CX", "Revenue Leadership"


def find_gaps():
    history = read_csv("performance_history.csv")
    leads = read_csv("leads.csv")
    funnel = read_csv("funnel_events.csv")
    close = read_csv("monthly_closing.csv")
    dq_path = "data_quality_report.csv"
    channels = summarize_channel_performance(history)
    paid_social = channels[channels["channel"] == "Paid Social"].iloc[0]
    paid_search = channels[channels["channel"] == "Paid Search"].iloc[0]
    referral = channels[channels["channel"] == "Referral"].iloc[0]
    crm = channels[channels["channel"] == "CRM / WhatsApp"].iloc[0]
    gaps = [
        gap("gap_001", "Marketing Analytics", "CAC", paid_social.cac, paid_search.cac, "high", "Paid Social concentra volume e apresenta CAC acima de canais de intenção.", "O mix de audiência pode estar gerando leads baratos com menor prontidão comercial.", "Cohort por criativo e qualidade de lead pós-venda.", "Quais conjuntos de anúncio geram matrícula ativada?", "Reduzir verba marginal em Paid Social e mover teste para Search, Referral e CRM.", "Head de Growth", "alta", "melhorar eficiência de aquisição", "CAC por canal e matrícula ativada"),
        gap("gap_002", "Revenue Analytics", "CPL vs conversion", paid_social.cpl, paid_search.cpl, "high", "CPL baixo não acompanha conversão final em matrícula.", "A promessa criativa pode atrair intenção baixa.", "Motivos de perda por campanha e escuta de calls.", "O lead entende preço, formato e compromisso antes da aula?", "Separar campanhas de volume e receita com metas diferentes.", "Marketing Analytics", "alta", "reduzir desperdício de SDR", "lead to enrollment"),
        gap("gap_003", "Growth", "LTV/CAC", referral.ltv_cac, channels["ltv_cac"].median(), "medium", "Referral tem LTV/CAC alto e baixo spend relativo.", "Há potencial subinvestido em indicação e comunidade.", "Capacidade de escala por coorte de indicação.", "Qual incentivo aumenta indicação sem degradar margem?", "Criar sprint de referral e creator-community.", "Head de Growth", "média", "crescer receita eficiente", "spend e LTV/CAC de Referral"),
        gap("gap_004", "Sales Ops", "P1 SLA", leads[(leads.priority_tier == "P1") & (leads.first_response_minutes > 240)].shape[0], 0, "high", "Existem leads P1 com resposta acima de 240 minutos.", "Fila comercial pode não estar priorizando intenção e timing.", "Agenda por SDR e motivo de atraso.", "Quais P1 perdem matrícula por atraso de contato?", "Criar SLA P1 de 15 minutos e alerta no CRM.", "Head Comercial", "alta", "aumentar conversão de leads quentes", "P1 response SLA"),
        gap("gap_005", "Funnel", "trial scheduled to attended", funnel["trial_class_date"].notna().mean(), 0.72, "medium", "Há perda relevante entre agendamento e presença em trial.", "Confirmação e lembrete podem estar fracos.", "Taxa por horário, SDR e canal.", "Quais horários e mensagens reduzem no-show?", "Testar lembrete WhatsApp e confirmação ativa.", "Sales Ops", "média", "aumentar matrícula sem mais mídia", "trial attended rate"),
        gap("gap_006", "Funnel", "free class attendance", funnel["attendance_date"].notna().mean(), 0.55, "high", "Gargalo entre inscrição em aula gratuita e presença.", "O compromisso do evento pode estar baixo em canais de volume.", "Show-up por tema, professor e antecedência.", "Qual tema tem melhor show-up e matrícula?", "Segmentar lembretes e encurtar janela até evento.", "Growth Ops", "alta", "melhorar conversão de eventos", "show-up rate"),
        gap("gap_007", "CRM", "CRM-assisted enrollment", crm.enrollments, paid_social.enrollments, "medium", "CRM / WhatsApp tem bom payback, mas menor escala.", "A base quente pode estar subutilizada.", "Inventário de leads reativáveis e consentimento.", "Quantos leads quentes podem receber cadência de recuperação?", "Criar régua de recuperação por intenção e attendance.", "Gerente de CRM", "média", "recuperar receita sem CAC incremental alto", "reativation conversion"),
        gap("gap_008", "Creator-led Growth", "quality variance", channels[channels.channel == "Influencers"].iloc[0].cac, paid_search.cac, "medium", "Influencers geram volume com variação de qualidade.", "Parte dos criadores atrai audiência desalinhada ao ticket.", "Receita assistida por creator e cohort de ativação.", "Quais criadores trazem alunos ativados?", "Trocar remuneração por CPA qualificado e receita assistida.", "Líder de Creators", "média", "reduzir variância de receita", "creator assisted revenue"),
        gap("gap_009", "Revenue Governance", "revenue vs CAC", close["cac_variation_pct"].max(), 0.05, "high", "Há mês com receita acima da meta e CAC piorando.", "O crescimento pode ter sido comprado por pressão de mídia.", "Margem por canal no mês.", "A receita incremental pagou o custo incremental?", "Separar crescimento saudável de crescimento comprado.", "Revenue Governance", "alta", "proteger margem", "margin-adjusted payback"),
        gap("gap_010", "Commercial", "leads vs enrollments", close["leads_variation_pct"].max(), close["enrollments_variation_pct"].max(), "high", "Leads acima da meta não garantem matrícula acima da meta.", "Qualidade e SLA podem estar limitando captura de demanda.", "Conversão por SDR, tier e resposta.", "Onde o funil perde P1 e P2?", "Roteamento por score e capacidade diária.", "Sales Ops", "alta", "converter demanda existente", "MQL to contacted"),
        gap("gap_011", "Product and CX", "activation_rate", close["activation_rate_actual"].min(), close["activation_rate_target"].mean(), "medium", "Ativação abaixo da meta em parte do período.", "Onboarding pode estar atrasando primeira aula.", "Eventos de produto e tickets de suporte.", "Qual fricção impede primeira aula até D7?", "Revisar onboarding, nudges e checklist de primeira aula.", "Head de Produto", "média", "aumentar retenção inicial", "activation in 7 days"),
        gap("gap_012", "Data Quality", "data completeness", "incompletudes sintéticas", "campos críticos completos", "medium", "Dados incompletos existem para owner, datas e justificativas.", "Processos de CRM e tracking podem gerar buracos decisórios.", "Dicionário de campos obrigatórios por sistema.", "Quais campos mudam decisão de investimento?", "Definir contrato de dados para CRM, mídia e produto.", "Data Governance", "média", "melhorar confiança executiva", "data_quality_score"),
    ]
    df = pd.DataFrame(gaps)
    df[["business_area", "problem_type", "responsible_team", "decision_owner"]] = df.apply(
        lambda r: pd.Series(classify_gap(r)), axis=1
    )
    save_csv(df, "consultant_gap_log.csv")
    lines = ["# Consultant Gap Review", "", "Os gaps abaixo usam evidências sintéticas e devem ser tratados como hipóteses para validação executiva.", ""]
    for _, r in df.iterrows():
        lines.append(f"## {r.gap_id} - {r.area}")
        lines.append(f"- Métrica: {r.metric}; severidade: {r.severity}.")
        lines.append(f"- Evidência: {r.evidence}")
        lines.append(f"- Hipótese provável: {r.likely_hypothesis}")
        lines.append(f"- Validação: {r.validation_question}")
        lines.append(f"- Ação recomendada: {r.recommended_action}")
        lines.append("")
    (DOCS / "consultant_gap_review.md").write_text("\n".join(lines), encoding="utf-8")
    return df


if __name__ == "__main__":
    result = find_gaps()
    print(f"Gaps gerados: {len(result)}")
