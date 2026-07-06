from pathlib import Path
import pandas as pd
from src.monthly_closing import classify_variation_problem

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def test_monthly_files_exist():
    for name in ["performance_targets.csv", "monthly_closing.csv", "variation_justifications.csv"]:
        assert (PROCESSED / name).exists()


def test_90_plus_days_and_baseline():
    history = pd.read_csv(PROCESSED / "performance_history.csv")
    assert pd.to_datetime(history["date"]).nunique() >= 90
    close = pd.read_csv(PROCESSED / "monthly_closing.csv")
    assert close.iloc[0]["closing_status"] == "baseline"


def test_monthly_variation_columns_and_no_infinite():
    close = pd.read_csv(PROCESSED / "monthly_closing.csv")
    cols = ["net_revenue_variation_abs", "net_revenue_variation_pct", "revenue_mom_variation_abs", "revenue_mom_variation_pct"]
    for col in cols:
        assert col in close.columns
        assert close[col].replace([float("inf"), -float("inf")], pd.NA).notna().all()


def test_relevant_variations_have_justification():
    close = pd.read_csv(PROCESSED / "monthly_closing.csv")
    just = pd.read_csv(PROCESSED / "variation_justifications.csv")
    relevant_months = set(close.loc[close["net_revenue_variation_pct"].abs() >= 0.08, "month"])
    assert relevant_months.issubset(set(just["month"]))


def test_variation_justifications_have_business_problem_fields():
    just = pd.read_csv(PROCESSED / "variation_justifications.csv")
    required = {
        "business_area",
        "problem_type",
        "responsible_team",
        "decision_owner",
        "escalation_level",
        "recommended_review_meeting",
    }
    assert required.issubset(just.columns)
    relevant = just[just["target_variation_pct"].abs() >= 0.08]
    assert relevant["business_area"].fillna("").str.len().gt(0).all()
    assert relevant["problem_type"].fillna("").str.len().gt(0).all()


def test_variation_taxonomies_are_valid():
    just = pd.read_csv(PROCESSED / "variation_justifications.csv")
    business_areas = {
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
        "Finance / Revenue + Paid Media",
        "Pricing / Offer",
        "Partnerships",
        "Mixed / Cross-functional",
    }
    problem_types = {
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
    assert just["business_area"].isin(business_areas).all()
    assert just["problem_type"].isin(problem_types).all()


def test_cac_activation_and_data_quality_classification_cases():
    cac = classify_variation_problem({
        "metric": "cac",
        "target_variation_pct": 0.18,
        "mom_variation_pct": 0.10,
        "detected_driver": "mix de mídia pressionado por investimento em canais de volume",
    })
    activation = classify_variation_problem({
        "metric": "activation_rate",
        "target_variation_pct": -0.12,
        "detected_driver": "sinal de falha no onboarding e ativação inicial",
    })
    data = classify_variation_problem({
        "metric": "tracking",
        "target_variation_pct": -0.10,
        "detected_driver": "campos nulos, IDs quebrados e inconsistência de tracking",
    })
    assert cac["business_area"] in {"Paid Media", "Marketing"}
    assert activation["business_area"] in {"Product", "CX / Student Success"}
    assert data["business_area"] == "Data / Tracking"
