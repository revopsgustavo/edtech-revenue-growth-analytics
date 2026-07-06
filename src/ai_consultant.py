import pandas as pd
try:
    from .utils import read_csv, DOCS
except ImportError:
    from utils import read_csv, DOCS

BANNED = ["a causa é", "foi comprovado", "com certeza", "garantidamente", "causa raiz confirmada"]


def generate_analysis():
    gaps = read_csv("consultant_gap_log.csv")
    close = read_csv("monthly_closing.csv")
    just = read_csv("variation_justifications.csv")
    actions = read_csv("action_tracker.csv")
    experiments = read_csv("experiment_recommendations.csv")
    best_growth = close.loc[close["revenue_mom_variation_pct"].idxmax(), "month"]
    worst_cac = close.loc[close["cac_mom_variation_pct"].idxmax(), "month"]
    farthest = close.iloc[(close["net_revenue_variation_pct"].abs()).idxmax()]["month"]
    driver = close["main_variation_driver"].mode().iloc[0]
    attention = "CAC e conversão de lead para matrícula"
    trend = "há indícios de tendência" if close["cac_actual"].tail(3).is_monotonic_increasing else "parece parcialmente pontual e precisa ser validado"
    healthy = "os dados sugerem crescimento parcialmente comprado com CAC pior" if (close["net_revenue_variation_pct"].max() > 0 and close["cac_variation_pct"].max() > 0) else "os dados sugerem crescimento mais saudável"
    critical_actions = actions[actions["priority"] == "critical"]
    top_area = actions["business_area"].mode().iloc[0] if not actions.empty else "sem área"
    negative_variations = just[just["target_variation_pct"] < 0].copy()
    positive_variations = just[just["target_variation_pct"] > 0].copy()
    negative_area = negative_variations["business_area"].mode().iloc[0] if not negative_variations.empty else "sem variação negativa relevante"
    positive_area = positive_variations["business_area"].mode().iloc[0] if not positive_variations.empty else "sem variação positiva relevante"
    main_problem = just["problem_type"].mode().iloc[0] if not just.empty else "mixed_driver"
    lead_investigator = just["decision_owner"].mode().iloc[0] if not just.empty else "Revenue Leadership"
    review_meeting = just["recommended_review_meeting"].mode().iloc[0] if not just.empty else "Monthly Business Review"
    next_metric = just["follow_up_metric"].mode().iloc[0] if not just.empty else "receita líquida, CAC e conversão"
    next_7 = actions.sort_values(["priority", "due_date"]).head(5)
    priority_experiments = experiments.head(5)
    lines = [
        "# AI Consultant Analysis",
        "",
        "## Veredito executivo",
        "Os dados sugerem que a EdTech tem alavancas claras de crescimento, mas a eficiência depende de separar volume barato de receita qualificada. Há indícios de que Referral, Paid Search, CRM / WhatsApp e eventos fortes sustentam melhor qualidade de receita do que campanhas focadas apenas em CPL.",
        "",
        "## 5 principais achados",
        "1. Paid Social gera volume, mas a evidência disponível aponta para CAC pressionado.",
        "2. Paid Search e Referral parecem menores em escala, porém melhores em intenção, payback e LTV/CAC.",
        "3. Aulas gratuitas influenciam conversão, mas o show-up ainda é um gargalo relevante.",
        "4. Leads P1 com atraso de atendimento sugerem risco de perda comercial evitável.",
        "5. CRM / WhatsApp mostra recuperação de receita com bom payback e pode estar subutilizado.",
        "",
        "## 5 decisões recomendadas",
        "1. Rebalancear orçamento de campanhas de volume para canais com melhor LTV/CAC.",
        "2. Implantar SLA P1 de 15 minutos e fila comercial por prioridade.",
        "3. Separar meta de leads de meta de matrícula ativada por canal.",
        "4. Escalar eventos com professor e tema de maior show-up, validando cohort de matrícula.",
        "5. Criar régua de CRM para leads quentes que assistiram aula ou responderam WhatsApp.",
        "",
        "## Gaps críticos",
    ]
    for _, r in gaps.head(8).iterrows():
        lines.append(f"- {r.area}: {r.evidence} Hipótese provável: {r.likely_hypothesis} Precisa ser validado com: {r.missing_evidence}")
    lines += [
        "",
        "## Hipóteses",
        "- Hipótese provável: campanhas com CPL baixo podem estar trazendo intenção insuficiente para conversão em matrícula.",
        "- Hipótese provável: a combinação evento, CRM e resposta rápida melhora a captura de demanda existente.",
        "- Hipótese provável: creators têm contribuição assistida, mas exigem medição por receita e ativação, não apenas leads.",
        "",
        "## Evidências ausentes",
        "- Margem real por plano, custo de professor e custo de suporte.",
        "- Motivos de perda auditados por call review.",
        "- Cohort de retenção por campanha após 60 e 90 dias.",
        "- Receita assistida multi-touch por creator.",
        "",
        "## Perguntas para liderança",
        "- Qual limite aceitável de CAC para crescer sem deteriorar margem?",
        "- Quais segmentos devem receber capacidade comercial prioritária?",
        "- A meta do mês privilegia receita bruta, receita líquida ou aluno ativado?",
        "",
        "## Plano de ação de 30 dias",
        "1. Semana 1: revisar orçamento por canal, campanha e tier de lead.",
        "2. Semana 2: ativar SLA P1 e cadência CRM para leads quentes.",
        "3. Semana 3: otimizar show-up de aulas gratuitas com teste de tema, horário e lembrete.",
        "4. Semana 4: fechar leitura de cohort por ativação, LTV/CAC e payback.",
        "",
        "## Métricas para acompanhar depois",
        "- CAC, LTV/CAC, lead to enrollment, show-up rate, P1 SLA, activation rate, retention proxy e expansion revenue.",
        "",
        "## Historical Performance and Monthly Variation",
        f"- Qual mês teve maior crescimento de receita? {best_growth}.",
        f"- Qual mês teve piora de CAC? {worst_cac}.",
        f"- A variação parece pontual ou tendência? {trend}.",
        "",
        "## Target vs Actual Closing",
        f"- Qual mês ficou mais distante da meta? {farthest}.",
        f"- Qual canal mais explicou a variação? A evidência disponível aponta para {driver}.",
        f"- Qual métrica mais merece atenção? {attention}.",
        f"- O resultado acima da meta foi saudável ou comprado com CAC pior? {healthy}.",
        "- Qual ação deve ser acompanhada no próximo fechamento? Rebalanceamento de verba e SLA P1 com leitura de matrícula ativada.",
        "",
        "## Business Area Diagnosis",
        f"- A evidência disponível sugere que a área mais relacionada à variação negativa é {negative_area}.",
        f"- A evidência disponível sugere que a área mais relacionada à variação positiva é {positive_area}.",
        f"- O principal ponto de investigação deveria estar em {main_problem}, validando se o problema é de aquisição, conversão, ativação, retenção, dados ou eficiência financeira.",
        f"- Quem deveria liderar a investigação: {lead_investigator}.",
        f"- O ritual recomendado para tratar o tema é {review_meeting}.",
        f"- A métrica a acompanhar no próximo ciclo é {next_metric}.",
        "- A hipótese precisa ser validada com cohort por canal, SLA comercial, qualidade de lead, ativação D7 e leitura financeira antes de qualquer decisão estrutural.",
        "",
        "## Plano de ação",
        f"- Ações críticas abertas: {len(critical_actions)}.",
        f"- Área com mais ações: {top_area}.",
        "- Ações para os próximos 7 dias:",
    ]
    for _, action in next_7.iterrows():
        lines.append(f"  - {action.action_id}: {action.recommended_action} Responsável: {action.owner}. Validar por {action.follow_up_metric}.")
    lines += [
        "",
        "## Experimentos recomendados",
    ]
    for _, exp in priority_experiments.iterrows():
        lines.append(f"### {exp.experiment_id} - {exp.experiment_name}")
        lines.append(f"- O experimento sugerido ajudaria a validar: {exp.hypothesis}")
        lines.append(f"- Área responsável: {exp.business_area}. Métrica primária: {exp.primary_metric}.")
        lines.append(f"- O critério mínimo de sucesso seria: {exp.minimum_success_criteria}")
        lines.append(f"- Risco: {exp.risk}. Prazo sugerido: {exp.suggested_duration_days} dias.")
        lines.append("- Não deve ser tratado como causa confirmada antes do teste.")
    text = "\n".join(lines)
    lowered = text.lower()
    for banned in BANNED:
        if banned in lowered:
            raise ValueError(f"Expressão proibida encontrada: {banned}")
    (DOCS / "ai_consultant_analysis.md").write_text(text, encoding="utf-8")
    print("Análise rule-based gerada")


if __name__ == "__main__":
    generate_analysis()
