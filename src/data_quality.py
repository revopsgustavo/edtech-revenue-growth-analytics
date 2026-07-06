import pandas as pd
try:
    from .utils import PROCESSED, read_csv, save_csv, DOCS
except ImportError:
    from utils import PROCESSED, read_csv, save_csv, DOCS

REQUIRED = {
    "campaigns.csv": ["campaign_id", "channel", "start_date", "end_date"],
    "daily_marketing_spend.csv": ["date", "campaign_id", "spend"],
    "leads.csv": ["lead_id", "campaign_id", "assigned_to_sales", "created_at"],
    "funnel_events.csv": ["lead_id", "lead_date", "current_stage"],
    "enrollments.csv": ["enrollment_id", "lead_id", "net_revenue"],
    "performance_targets.csv": ["month", "channel", "target_net_revenue"],
    "monthly_closing.csv": ["month", "net_revenue_actual", "net_revenue_target"],
    "variation_justifications.csv": ["month", "metric", "actual_value"],
}


def add(rows, check_name, table, status, issue_count, evidence, revenue_impact):
    rows.append({
        "check_name": check_name,
        "table_name": table,
        "status": status,
        "issue_count": int(issue_count),
        "evidence": evidence,
        "revenue_impact": revenue_impact,
        "recommendation": "Corrigir origem do dado e monitorar no próximo fechamento.",
    })


def run_quality_checks():
    rows = []
    for filename, cols in REQUIRED.items():
        path = PROCESSED / filename
        if not path.exists():
            add(rows, "file_exists", filename, "fail", 1, "Arquivo ausente.", "Bloqueia análise executiva.")
            continue
        df = pd.read_csv(path)
        missing_cols = [c for c in cols if c not in df.columns]
        add(rows, "required_fields", filename, "fail" if missing_cols else "pass", len(missing_cols), ", ".join(missing_cols) or "Campos obrigatórios presentes.", "Campos ausentes reduzem confiança em CAC, receita e fechamento.")
        nulls = df[[c for c in cols if c in df.columns]].isna().sum().sum()
        add(rows, "required_nulls", filename, "warn" if nulls else "pass", nulls, f"{nulls} nulos em campos críticos.", "Nulos podem afetar roteamento, metas e atribuição.")
    leads = read_csv("leads.csv")
    campaigns = read_csv("campaigns.csv")
    spend = read_csv("daily_marketing_spend.csv")
    funnel = read_csv("funnel_events.csv")
    enroll = read_csv("enrollments.csv")
    targets = read_csv("performance_targets.csv")
    close = read_csv("monthly_closing.csv")
    just = read_csv("variation_justifications.csv")
    add(rows, "leads_without_campaign", "leads.csv", "fail" if (~leads.campaign_id.isin(campaigns.campaign_id)).sum() else "pass", (~leads.campaign_id.isin(campaigns.campaign_id)).sum(), "Leads sem campanha válida.", "Afeta ROI e atribuição.")
    add(rows, "leads_without_owner", "leads.csv", "warn" if leads.assigned_to_sales.isna().sum() else "pass", leads.assigned_to_sales.isna().sum(), "Leads sem owner comercial.", "Pode gerar perda de receita por SLA.")
    inconsistent = ((pd.to_datetime(funnel["enrollment_date"], errors="coerce").notna()) & (pd.to_datetime(funnel["lead_date"], errors="coerce").isna())).sum()
    add(rows, "inconsistent_funnel", "funnel_events.csv", "fail" if inconsistent else "pass", inconsistent, "Matrícula sem lead_date.", "Quebra leitura de conversão.")
    add(rows, "enrollment_without_lead", "enrollments.csv", "fail" if (~enroll.lead_id.isin(leads.lead_id)).sum() else "pass", (~enroll.lead_id.isin(leads.lead_id)).sum(), "Matrícula sem lead.", "Afeta CAC e origem de receita.")
    add(rows, "spend_without_campaign_id", "daily_marketing_spend.csv", "fail" if spend.campaign_id.isna().sum() else "pass", spend.campaign_id.isna().sum(), "Spend sem campaign_id.", "Afeta ROAS.")
    negatives = 0
    for df in [spend, enroll, targets, close]:
        nums = df.select_dtypes("number")
        allowed_negative = [c for c in nums.columns if "variation" in c or "roi" in c]
        nums = nums.drop(columns=allowed_negative, errors="ignore")
        negatives += int((nums < 0).sum().sum())
    add(rows, "negative_values", "all", "fail" if negatives else "pass", negatives, "Valores negativos indevidos.", "Pode distorcer métricas financeiras.")
    duplicates = leads.lead_id.duplicated().sum() + campaigns.campaign_id.duplicated().sum()
    add(rows, "duplicates", "core_ids", "fail" if duplicates else "pass", duplicates, "IDs duplicados.", "Afeta contagem executiva.")
    add(rows, "missing_targets", "performance_targets.csv", "fail" if targets.empty else "pass", 0 if not targets.empty else 1, "Metas presentes.", "Sem metas não há governança de performance.")
    add(rows, "monthly_closing_without_month", "monthly_closing.csv", "fail" if close.month.isna().sum() else "pass", close.month.isna().sum(), "Fechamento sem mês.", "Bloqueia fechamento.")
    add(rows, "variation_without_actual", "variation_justifications.csv", "fail" if just.actual_value.isna().sum() else "pass", just.actual_value.isna().sum(), "Variação sem atual.", "Enfraquece justificativa.")
    add(rows, "justification_without_metric", "variation_justifications.csv", "fail" if just.metric.isna().sum() else "pass", just.metric.isna().sum(), "Justificativa sem métrica.", "Dificulta decisão.")
    report = pd.DataFrame(rows)
    save_csv(report, "data_quality_report.csv")
    md = ["# Textura de Qualidade de Dados", "", "A análise trata qualidade como risco de receita, não como checklist técnico.", ""]
    for _, r in report.iterrows():
        md.append(f"- {r.check_name} em {r.table_name}: {r.status} ({r.issue_count}). Impacto: {r.revenue_impact}")
    (DOCS / "data_quality_report.md").write_text("\n".join(md), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run_quality_checks()
    failures = (result["status"] == "fail").sum()
    print(f"Data quality gerado: {len(result)} checks, {failures} falhas")
