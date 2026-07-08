import pandas as pd
import numpy as np
try:
    from .metrics import calculate_cac, calculate_cpl, calculate_roi, calculate_roas, calculate_ltv_cac, variation_abs, variation_pct, status_vs_target
    from .utils import brl, br_number, br_pct, read_csv, save_csv, DOCS, safe_div
except ImportError:
    from metrics import calculate_cac, calculate_cpl, calculate_roi, calculate_roas, calculate_ltv_cac, variation_abs, variation_pct, status_vs_target
    from utils import brl, br_number, br_pct, read_csv, save_csv, DOCS, safe_div

METRICS = ["spend", "leads", "enrollments", "net_revenue", "cac", "cpl", "roi", "roas", "ltv_cac", "activation_rate", "engagement_score", "retention_proxy", "expansion_revenue"]
BUSINESS_AREAS = {
    "Marketing",
    "Paid Media",
    "Organic / Content",
    "Creator / Influencer",
    "CRM / Lifecycle",
    "Sales",
    "Sales Ops",
    "Product",
    "CX / Student Success",
    "Data / Tracking",
    "Finance / Revenue",
    "Pricing / Offer",
    "Partnerships",
    "Mixed / Cross-functional",
    "Finance / Revenue + Paid Media",
}
PROBLEM_TYPES = {
    "acquisition_efficiency",
    "lead_quality",
    "funnel_conversion",
    "sales_sla",
    "campaign_roi",
    "content_performance",
    "event_attendance",
    "activation_gap",
    "engagement_gap",
    "retention_risk",
    "expansion_opportunity",
    "crm_reactivation",
    "data_quality",
    "pricing_discount",
    "target_miss",
    "margin_pressure",
    "mixed_driver",
}


def build_performance_history():
    daily = read_csv("daily_marketing_spend.csv", parse_dates=["date"])
    leads = read_csv("leads.csv", parse_dates=["created_at"])
    funnel = read_csv("funnel_events.csv", parse_dates=["lead_date", "mql_date", "sales_contact_date", "trial_class_date", "enrollment_date", "activation_date"])
    enroll = read_csv("enrollments.csv", parse_dates=["enrollment_date"])
    activation = read_csv("student_activation.csv")
    engagement = read_csv("learning_engagement.csv")
    expansion = read_csv("expansion_opportunities.csv")
    lead_dim = leads[["lead_id", "created_at", "campaign_id", "channel", "language_interest"]]
    lf = lead_dim.merge(funnel, on="lead_id", how="left")
    le = lf.merge(enroll[["lead_id", "net_revenue", "expected_ltv"]], on="lead_id", how="left")
    le["date"] = pd.to_datetime(le["created_at"]).dt.date
    agg = le.groupby(["date", "channel", "campaign_id"], as_index=False).agg(
        leads=("lead_id", "count"),
        mqls=("mql_date", lambda s: s.notna().sum()),
        sales_contacts=("sales_contact_date", lambda s: s.notna().sum()),
        trial_scheduled=("trial_class_date", lambda s: s.notna().sum()),
        trial_attended=("trial_class_date", lambda s: s.notna().sum()),
        enrollments=("enrollment_date", lambda s: s.notna().sum()),
        net_revenue=("net_revenue", "sum"),
        expected_ltv=("expected_ltv", "sum"),
    )
    daily["date"] = pd.to_datetime(daily["date"]).dt.date
    spend = daily.groupby(["date", "channel", "campaign_id"], as_index=False).agg(spend=("spend", "sum"))
    agg["date"] = pd.to_datetime(agg["date"]).dt.date
    history = spend.merge(agg, on=["date", "channel", "campaign_id"], how="left").fillna(0)
    history["date"] = pd.to_datetime(history["date"])
    history["month"] = history["date"].dt.to_period("M").astype(str)
    history["week"] = history["date"].dt.isocalendar().week.astype(int)
    campaigns = read_csv("campaigns.csv")
    history = history.merge(campaigns[["campaign_id", "audience_segment"]], on="campaign_id", how="left")
    act_rate = safe_div((activation["activation_status"] == "activated").sum(), len(activation))
    eng_score = engagement["engagement_score"].mean()
    retention = 1 - safe_div(read_csv("students.csv")["churn_risk_score"].mean(), 100)
    exp_total = expansion["expected_expansion_revenue"].sum()
    history["active_students"] = history["enrollments"].cumsum()
    history["cac"] = history.apply(lambda r: calculate_cac(r.spend, r.enrollments), axis=1)
    history["cpl"] = history.apply(lambda r: calculate_cpl(r.spend, r.leads), axis=1)
    history["roi"] = history.apply(lambda r: calculate_roi(r.net_revenue, r.spend), axis=1)
    history["roas"] = history.apply(lambda r: calculate_roas(r.net_revenue, r.spend), axis=1)
    history["ltv_cac"] = history.apply(lambda r: calculate_ltv_cac(safe_div(r.expected_ltv, r.enrollments), r.cac), axis=1)
    history["payback_months"] = history.apply(lambda r: safe_div(r.cac, safe_div(r.expected_ltv, 12)), axis=1)
    history["activation_rate"] = act_rate
    history["engagement_score"] = eng_score
    history["retention_proxy"] = retention
    history["expansion_revenue"] = exp_total / max(1, len(history))
    return history


def build_targets(history):
    monthly_channel = history.groupby(["month", "channel"], as_index=False).agg(
        target_spend=("spend", "sum"),
        target_leads=("leads", "sum"),
        target_mqls=("mqls", "sum"),
        target_enrollments=("enrollments", "sum"),
        target_net_revenue=("net_revenue", "sum"),
        target_activation_rate=("activation_rate", "mean"),
        target_engagement_score=("engagement_score", "mean"),
        target_retention_proxy=("retention_proxy", "mean"),
        target_expansion_revenue=("expansion_revenue", "sum"),
    )
    multipliers = {"2026-04": 0.88, "2026-05": 0.92}
    for col in ["target_spend", "target_leads", "target_mqls", "target_enrollments", "target_net_revenue"]:
        monthly_channel[col] = monthly_channel.apply(lambda r: round(r[col] * multipliers.get(r.month, 1.08), 2), axis=1)
    monthly_channel["target_cac"] = monthly_channel.apply(lambda r: calculate_cac(r.target_spend, r.target_enrollments), axis=1)
    monthly_channel["target_cpl"] = monthly_channel.apply(lambda r: calculate_cpl(r.target_spend, r.target_leads), axis=1)
    monthly_channel["target_roi"] = monthly_channel.apply(lambda r: calculate_roi(r.target_net_revenue, r.target_spend), axis=1)
    monthly_channel["target_roas"] = monthly_channel.apply(lambda r: calculate_roas(r.target_net_revenue, r.target_spend), axis=1)
    monthly_channel["target_ltv_cac"] = np.where(monthly_channel["target_cac"] > 0, 3.1, 0)
    return monthly_channel


def driver_for(row):
    if row["net_revenue_variation_pct"] > 0.12 and row["cac_variation_pct"] > 0.08:
        return "crescimento de receita comprado com CAC acima da meta"
    if row["leads_variation_pct"] > 0.10 and row["enrollments_variation_pct"] < -0.05:
        return "volume de leads sem conversão proporcional em matrícula"
    if row["activation_rate_variation_pct"] < -0.08:
        return "sinal de falha no onboarding e ativação inicial"
    if row["net_revenue_variation_pct"] > 0.10:
        return "evento forte e melhor conversão de oferta"
    if row["cac_variation_pct"] > 0.10:
        return "mix de mídia pressionado por investimento em canais de volume"
    return "variação distribuída entre mix de canal, conversão e ticket"


def classify_variation_problem(row):
    metric = str(row.get("metric", "")).lower()
    driver = str(row.get("detected_driver", row.get("main_variation_driver", ""))).lower()
    target_pct = float(row.get("target_variation_pct", row.get(f"{metric}_variation_pct", 0)) or 0)
    mom_pct = float(row.get("mom_variation_pct", 0) or 0)
    net_revenue_pct = float(row.get("net_revenue_variation_pct", 0) or 0)
    cac_pct = float(row.get("cac_variation_pct", 0) or 0)
    leads_pct = float(row.get("leads_variation_pct", 0) or 0)
    enrollments_pct = float(row.get("enrollments_variation_pct", 0) or 0)

    result = {
        "business_area": "Mixed / Cross-functional",
        "problem_type": "mixed_driver",
        "responsible_team": "Marketing + Sales + CX",
        "decision_owner": "Revenue Leadership",
        "escalation_level": "team",
        "recommended_review_meeting": "Monthly Business Review",
    }

    if any(term in driver for term in ["tracking", "campos nulos", "ids quebrados", "inconsist"]) or metric in {"data_quality", "tracking"}:
        return {
            **result,
            "business_area": "Data / Tracking",
            "problem_type": "data_quality",
            "responsible_team": "Data Engineering / Analytics",
            "decision_owner": "Data Lead",
            "recommended_review_meeting": "Data Quality Review",
        }
    if net_revenue_pct > 0 and cac_pct > 0.08:
        return {
            **result,
            "business_area": "Finance / Revenue + Paid Media",
            "problem_type": "margin_pressure",
            "responsible_team": "Revenue / Growth",
            "decision_owner": "Head de Growth ou Finance Partner",
            "escalation_level": "leadership",
            "recommended_review_meeting": "Monthly Business Review",
        }
    if leads_pct > 0.10 and enrollments_pct < -0.05:
        return {
            **result,
            "business_area": "Sales",
            "problem_type": "funnel_conversion",
            "responsible_team": "Sales / SDR Team",
            "decision_owner": "Head Comercial",
            "recommended_review_meeting": "Weekly Sales Pipeline Review",
        }
    if "leads p1" in driver or "sla" in driver or "resposta lenta" in driver:
        return {
            **result,
            "business_area": "Sales Ops",
            "problem_type": "sales_sla",
            "responsible_team": "SDR Team",
            "decision_owner": "Líder de Sales Ops",
            "recommended_review_meeting": "Sales Ops SLA Review",
        }
    if "show-up" in driver or "aula gratuita" in driver or "evento" in driver:
        return {
            **result,
            "business_area": "Organic / Content",
            "problem_type": "event_attendance",
            "responsible_team": "Content / Events",
            "decision_owner": "Líder de Growth",
            "recommended_review_meeting": "Growth Weekly",
        }
    if metric == "activation_rate" or "ativação" in driver or "onboarding" in driver:
        return {
            **result,
            "business_area": "Product",
            "problem_type": "activation_gap",
            "responsible_team": "Product / CX",
            "decision_owner": "Head de Produto ou Head de CX",
            "recommended_review_meeting": "Product and CX Review",
        }
    if metric == "engagement_score" or "engajamento" in driver:
        return {
            **result,
            "business_area": "CX / Student Success",
            "problem_type": "engagement_gap",
            "responsible_team": "Student Success",
            "decision_owner": "Head de CX",
            "recommended_review_meeting": "CX Health Review",
        }
    if metric == "retention_proxy" or "churn" in driver or "retenção" in driver:
        return {
            **result,
            "business_area": "CX / Student Success",
            "problem_type": "retention_risk",
            "responsible_team": "Student Success",
            "decision_owner": "Head de CX",
            "recommended_review_meeting": "Retention Review",
        }
    if metric in {"cac", "cpl", "spend", "roas", "roi"} and (target_pct > 0 or mom_pct > 0 or "cac" in driver or "mídia" in driver):
        return {
            **result,
            "business_area": "Paid Media",
            "problem_type": "campaign_roi" if metric in {"roi", "roas"} else "acquisition_efficiency",
            "responsible_team": "Growth / Paid Media",
            "decision_owner": "Head de Marketing ou Líder de Growth",
            "recommended_review_meeting": "Growth Weekly",
        }
    if metric == "expansion_revenue":
        return {
            **result,
            "business_area": "CX / Student Success",
            "problem_type": "expansion_opportunity",
            "responsible_team": "Student Success",
            "decision_owner": "Head de CX",
            "recommended_review_meeting": "Revenue Expansion Review",
        }
    if metric == "net_revenue" and target_pct < 0:
        return {
            **result,
            "business_area": "Sales",
            "problem_type": "target_miss",
            "responsible_team": "Sales / Growth",
            "decision_owner": "Revenue Leadership",
            "recommended_review_meeting": "Monthly Business Review",
        }
    return result


def build_monthly_closing(history, targets):
    actual = history.groupby("month", as_index=False).agg(
        spend_actual=("spend", "sum"),
        leads_actual=("leads", "sum"),
        enrollments_actual=("enrollments", "sum"),
        net_revenue_actual=("net_revenue", "sum"),
        expected_ltv_actual=("expected_ltv", "sum"),
        activation_rate_actual=("activation_rate", "mean"),
        engagement_score_actual=("engagement_score", "mean"),
        retention_proxy_actual=("retention_proxy", "mean"),
        expansion_revenue_actual=("expansion_revenue", "sum"),
    )
    actual["cac_actual"] = actual.apply(lambda r: calculate_cac(r.spend_actual, r.enrollments_actual), axis=1)
    actual["cpl_actual"] = actual.apply(lambda r: calculate_cpl(r.spend_actual, r.leads_actual), axis=1)
    actual["roi_actual"] = actual.apply(lambda r: calculate_roi(r.net_revenue_actual, r.spend_actual), axis=1)
    actual["roas_actual"] = actual.apply(lambda r: calculate_roas(r.net_revenue_actual, r.spend_actual), axis=1)
    actual["ltv_cac_actual"] = actual.apply(lambda r: calculate_ltv_cac(safe_div(r.expected_ltv_actual, r.enrollments_actual), r.cac_actual), axis=1)
    # Rate and score targets are channel-level benchmarks; monthly closing must average them, not sum them.
    target_month = targets.groupby("month", as_index=False).agg(
        target_spend=("target_spend", "sum"),
        target_leads=("target_leads", "sum"),
        target_mqls=("target_mqls", "sum"),
        target_enrollments=("target_enrollments", "sum"),
        target_net_revenue=("target_net_revenue", "sum"),
        target_activation_rate=("target_activation_rate", "mean"),
        target_engagement_score=("target_engagement_score", "mean"),
        target_retention_proxy=("target_retention_proxy", "mean"),
        target_expansion_revenue=("target_expansion_revenue", "sum"),
        target_ltv_cac=("target_ltv_cac", "mean"),
    )
    target_month["target_cac"] = target_month.apply(lambda r: calculate_cac(r.target_spend, r.target_enrollments), axis=1)
    target_month["target_cpl"] = target_month.apply(lambda r: calculate_cpl(r.target_spend, r.target_leads), axis=1)
    target_month["target_roi"] = target_month.apply(lambda r: calculate_roi(r.target_net_revenue, r.target_spend), axis=1)
    target_month["target_roas"] = target_month.apply(lambda r: calculate_roas(r.target_net_revenue, r.target_spend), axis=1)
    target_month = target_month.rename(columns={c: c.replace("target_", "") + "_target" for c in target_month.columns if c.startswith("target_")})
    close = actual.merge(target_month, on="month", how="left")
    for metric in METRICS:
        close[f"{metric}_variation_abs"] = close.apply(lambda r: variation_abs(r[f"{metric}_actual"], r[f"{metric}_target"]), axis=1)
        close[f"{metric}_variation_pct"] = close.apply(lambda r: variation_pct(r[f"{metric}_actual"], r[f"{metric}_target"]), axis=1)
    close = close.sort_values("month").reset_index(drop=True)
    for metric in ["net_revenue", "cac", "enrollments"]:
        close[f"previous_month_{metric.replace('net_revenue', 'revenue')}"] = close[f"{metric}_actual"].shift(1).fillna(0)
        prev_col = f"previous_month_{metric.replace('net_revenue', 'revenue')}"
        close[f"{metric.replace('net_revenue', 'revenue')}_mom_variation_abs"] = close[f"{metric}_actual"] - close[prev_col]
        close[f"{metric.replace('net_revenue', 'revenue')}_mom_variation_pct"] = close.apply(lambda r: 0 if r[prev_col] == 0 else (r[f"{metric}_actual"] - r[prev_col]) / r[prev_col], axis=1)
    close["main_variation_driver"] = close.apply(driver_for, axis=1)
    close["target_status"] = close.apply(lambda r: status_vs_target("net_revenue", r.net_revenue_actual, r.net_revenue_target), axis=1)
    close["closing_status"] = close.apply(lambda r: "baseline" if r.name == 0 else ("aprovado" if r.target_status != "behind" else "revisar plano"), axis=1)
    return close


def build_justifications(close):
    rows = []
    owners = {"net_revenue": "Head de Growth", "cac": "Marketing Analytics", "activation_rate": "Head de Produto", "enrollments": "Head Comercial"}
    for _, row in close.iterrows():
        for metric in ["net_revenue", "cac", "activation_rate", "enrollments"]:
            relevant = abs(row[f"{metric}_variation_pct"]) >= 0.08 or row["month"] == close["month"].min()
            if not relevant:
                continue
            item = {
                "justification_id": f"just_{len(rows) + 1:04d}",
                "month": row["month"],
                "metric": metric,
                "actual_value": row[f"{metric}_actual"],
                "target_value": row[f"{metric}_target"],
                "target_variation_abs": row[f"{metric}_variation_abs"],
                "target_variation_pct": row[f"{metric}_variation_pct"],
                "previous_month_value": row.get("previous_month_revenue", 0) if metric == "net_revenue" else row.get(f"previous_month_{metric}", 0),
                "mom_variation_abs": row.get("revenue_mom_variation_abs", 0) if metric == "net_revenue" else row.get(f"{metric}_mom_variation_abs", 0),
                "mom_variation_pct": row.get("revenue_mom_variation_pct", 0) if metric == "net_revenue" else row.get(f"{metric}_mom_variation_pct", 0),
                "detected_driver": row["main_variation_driver"],
                "analyst_justification": "Os dados sugerem variação associada ao mix de canais, intensidade de eventos e qualidade de conversão no período.",
                "business_context": "Fechamento sintético para uma EdTech digital com mídia, creator-led growth, CRM e funil comercial.",
                "action_taken": "Rebalancear investimento, revisar SLA comercial e acompanhar conversão de aula gratuita para matrícula.",
                "owner": owners[metric],
                "follow_up_metric": "receita líquida, CAC, conversão por etapa e ativação em 7 dias",
                "created_at": pd.Timestamp.now().date(),
            }
            item.update(classify_variation_problem({
                **row.to_dict(),
                **item,
                "detected_driver": row["main_variation_driver"],
            }))
            rows.append(item)
    columns = [
        "justification_id",
        "month",
        "metric",
        "business_area",
        "problem_type",
        "responsible_team",
        "decision_owner",
        "escalation_level",
        "recommended_review_meeting",
        "actual_value",
        "target_value",
        "target_variation_abs",
        "target_variation_pct",
        "previous_month_value",
        "mom_variation_abs",
        "mom_variation_pct",
        "detected_driver",
        "analyst_justification",
        "business_context",
        "action_taken",
        "owner",
        "follow_up_metric",
        "created_at",
    ]
    return pd.DataFrame(rows, columns=columns)


def write_analysis(close, just):
    money_metrics = {"net_revenue", "spend", "cac", "cpl", "expansion_revenue"}

    def fmt_metric(metric, value):
        if metric in money_metrics:
            return brl(value)
        return br_number(value, 2)

    lines = ["# Análise de Fechamento Mensal", ""]
    for _, r in close.iterrows():
        lines += [
            f"## {r.month}",
            f"- Meta de receita: {brl(r.net_revenue_target)}; realizado: {brl(r.net_revenue_actual)}; variação: {br_pct(r.net_revenue_variation_pct)}.",
            f"- Meta de CAC: {brl(r.cac_target)}; realizado: {brl(r.cac_actual)}; variação: {br_pct(r.cac_variation_pct)}.",
            f"- Driver provável: {r.main_variation_driver}.",
            "- Risco: eficiência de aquisição e ativação inicial precisam ser monitoradas junto com volume.",
            "- Oportunidade: priorizar segmentos com LTV/CAC superior e recuperar leads quentes por CRM/WhatsApp.",
            "- Recomendação: revisar orçamento por canal no próximo fechamento e validar hipóteses com cohort de origem.",
            "",
        ]
    lines += [
        "## Área de Problema por Variação Mensal",
        "",
        "| Mês | Métrica | Meta | Realizado | Variação | Setor responsável provável | Tipo de problema | Responsável pela decisão | Ação recomendada |",
        "|---|---|---:|---:|---:|---|---|---|---|",
    ]
    for _, r in just.iterrows():
        lines.append(
            f"| {r.month} | {r.metric} | {fmt_metric(r.metric, r.target_value)} | {fmt_metric(r.metric, r.actual_value)} | {br_pct(r.target_variation_pct)} | "
            f"{r.business_area} | {r.problem_type} | {r.decision_owner} | {r.action_taken} |"
        )
    (DOCS / "monthly_closing_analysis.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    history = build_performance_history()
    targets = build_targets(history)
    close = build_monthly_closing(history, targets)
    just = build_justifications(close)
    save_csv(history, "performance_history.csv")
    save_csv(targets, "performance_targets.csv")
    save_csv(close, "monthly_closing.csv")
    save_csv(just, "variation_justifications.csv")
    write_analysis(close, just)
    print(f"Fechamento mensal gerado: {len(close)} meses")


if __name__ == "__main__":
    main()
