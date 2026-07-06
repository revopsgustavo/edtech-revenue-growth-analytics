import pandas as pd

try:
    from .utils import read_csv, save_csv, DOCS
except ImportError:
    from utils import read_csv, save_csv, DOCS

EXPERIMENT_TYPES = {
    "campaign_test", "offer_test", "crm_test", "sales_sla_test",
    "onboarding_test", "activation_test", "pricing_test",
    "content_test", "event_test",
}
STATUSES = {"proposed", "approved", "running", "completed", "discarded"}


def experiment_row(idx, month, area, problem, hypothesis, name, exp_type, segment, primary, secondary, impact, criteria, risk, owner, days):
    return {
        "experiment_id": f"exp_{idx:04d}",
        "month": month,
        "business_area": area,
        "problem_type": problem,
        "hypothesis": hypothesis,
        "experiment_name": name,
        "experiment_type": exp_type,
        "target_segment": segment,
        "primary_metric": primary,
        "secondary_metric": secondary,
        "expected_impact": impact,
        "minimum_success_criteria": criteria,
        "risk": risk,
        "owner": owner,
        "suggested_duration_days": days,
        "status": "proposed",
    }


def generate_experiments():
    gaps = read_csv("consultant_gap_log.csv")
    closing = read_csv("monthly_closing.csv")
    justifications = read_csv("variation_justifications.csv")
    latest_month = closing["month"].max()
    rows = []
    next_id = 1

    def add(*args):
        nonlocal next_id
        rows.append(experiment_row(next_id, *args))
        next_id += 1

    if (gaps["metric"].str.contains("CAC", case=False, na=False)).any():
        add(latest_month, "Marketing Analytics", "CAC alto em canal de volume",
            "A hipótese a testar é que restringir audiência e criativo por intenção aumenta matrícula ativada sem elevar CPL de forma desproporcional.",
            "Paid Social qualificado vs volume", "campaign_test", "leads de Paid Social P2/P3",
            "CAC por matrícula ativada", "lead to enrollment", "Reduzir CAC em canal de escala.",
            "Reduzir CAC em 12% mantendo ao menos 85% do volume de matrículas ativadas.",
            "Pode reduzir volume total de leads no curto prazo.", "Head de Growth", 21)

    if (closing["leads_variation_pct"].max() > 0.08) and (closing["enrollments_variation_pct"].min() < 0):
        add(latest_month, "Sales Ops", "Leads acima da meta com matrícula abaixo",
            "A hipótese a testar é que priorização por tier e SLA curto aumenta conversão sem aumentar mídia.",
            "Fila P1 com SLA de 15 minutos", "sales_sla_test", "P1 e P2 com alta intenção",
            "P1 lead to enrollment", "first_response_minutes", "Aumentar captura de demanda já gerada.",
            "Aumentar conversão P1 em 10% e reduzir mediana de resposta para menos de 15 minutos.",
            "Pode deslocar capacidade comercial de leads nurture.", "Head Comercial", 14)

    if (closing["activation_rate_variation_pct"].min() < -0.05):
        add(latest_month, "Product and CX", "Ativação abaixo da meta",
            "A hipótese a testar é que nudges de onboarding e agendamento da primeira aula reduzem atraso até ativação.",
            "Onboarding D0-D7 com nudges", "onboarding_test", "novos alunos premium",
            "activation_rate", "days_to_first_class", "Melhorar retenção inicial e qualidade de receita.",
            "Aumentar activation_rate em 8% e reduzir days_to_first_class em 1 dia.",
            "Pode aumentar mensagens sem melhorar valor percebido.", "Head de Produto", 28)

    if (gaps["metric"].str.contains("free class attendance", case=False, na=False)).any():
        add(latest_month, "Growth Ops", "Show-up de evento baixo",
            "A hipótese a testar é que lembrete WhatsApp com promessa específica aumenta presença em aula gratuita.",
            "Lembrete de evento por intenção", "event_test", "inscritos em aulas gratuitas",
            "show_up_rate", "event revenue per attendee", "Aumentar receita por evento sem elevar spend.",
            "Aumentar show_up_rate em 10% e manter conversão para matrícula.",
            "Mensagem pode atrair presença pouco qualificada se a promessa for ampla.", "Growth Ops", 14)

    if (gaps["area"].str.contains("CRM", case=False, na=False)).any():
        add(latest_month, "CRM", "CRM subutilizado",
            "A hipótese a testar é que cadência baseada em presença e resposta recupera leads quentes com payback melhor.",
            "Régua WhatsApp pós-aula", "crm_test", "leads que compareceram e não compraram",
            "reactivation conversion", "CRM-assisted enrollment", "Recuperar receita com baixo CAC incremental.",
            "Gerar conversão de recuperação acima de 6% sem aumentar opt-out.",
            "Excesso de contato pode reduzir resposta futura.", "Gerente de CRM", 21)

    if (gaps["area"].str.contains("Creator", case=False, na=False)).any():
        add(latest_month, "Creator-led Growth", "Lead sem matrícula por conteúdo",
            "A hipótese a testar é que creators com CTA para aula diagnóstica geram menos volume, mas maior matrícula ativada.",
            "CTA creator para diagnóstico", "content_test", "audiências de creators educacionais",
            "content to enrollment assisted conversion", "creator assisted revenue", "Aumentar qualidade da receita assistida.",
            "Aumentar conversão assistida em 8% com queda de leads menor que 20%.",
            "Pode reduzir alcance se o CTA ficar muito transacional.", "Líder de Creators", 21)

    if (justifications["metric"].str.contains("cac", case=False, na=False)).any():
        add(latest_month, "Revenue Governance", "Desconto e margem",
            "A hipótese a testar é que oferta com bônus de valor preserva margem melhor que desconto direto.",
            "Bônus premium vs desconto", "pricing_test", "leads P1 em fase de oferta",
            "margin-adjusted payback", "net_revenue", "Melhorar payback sem reduzir conversão de oferta.",
            "Melhorar payback ajustado em 10% com conversão não inferior ao controle.",
            "Pode reduzir conversão se o bônus não for percebido como valor.", "Revenue Governance", 28)

    experiments = pd.DataFrame(rows).drop_duplicates(subset=["experiment_name"])
    save_csv(experiments, "experiment_recommendations.csv")
    write_doc(experiments)
    return experiments


def write_doc(experiments):
    lines = [
        "# Recomendações de Experimentos",
        "",
        "## Resumo dos experimentos",
        f"Foram propostos {len(experiments)} experimentos mensuráveis para validar hipóteses antes de decisões de escala.",
        "",
        "## Hipóteses, métricas e critérios de sucesso",
    ]
    for _, row in experiments.iterrows():
        lines += [
            f"### {row.experiment_id} - {row.experiment_name}",
            f"- Hipótese: {row.hypothesis}",
            f"- Área: {row.business_area}. Tipo: {row.experiment_type}. Responsável: {row.owner}.",
            f"- Métrica primária: {row.primary_metric}. Métrica secundária: {row.secondary_metric}.",
            f"- Critério mínimo de sucesso: {row.minimum_success_criteria}",
            f"- Risco: {row.risk}",
            "",
        ]
    lines += [
        "## Priorização",
        "- Priorizar testes ligados a CAC, SLA P1, show-up de eventos e ativação inicial.",
        "- Não tratar nenhum resultado como causa confirmada antes de teste controlado e leitura de cohort.",
        "",
        "## Próximos passos",
        "- Aprovar owners e duração.",
        "- Definir grupo controle quando possível.",
        "- Registrar resultado no próximo fechamento mensal.",
    ]
    (DOCS / "experiment_recommendations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = generate_experiments()
    print(f"Experimentos recomendados: {len(result)}")
