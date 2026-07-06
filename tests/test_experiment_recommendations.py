from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

REQUIRED = {
    "experiment_id", "month", "business_area", "problem_type", "hypothesis",
    "experiment_name", "experiment_type", "target_segment", "primary_metric",
    "secondary_metric", "expected_impact", "minimum_success_criteria", "risk",
    "owner", "suggested_duration_days", "status",
}
TYPES = {
    "campaign_test", "offer_test", "crm_test", "sales_sla_test",
    "onboarding_test", "activation_test", "pricing_test",
    "content_test", "event_test",
}
STATUSES = {"proposed", "approved", "running", "completed", "discarded"}


def test_experiment_recommendations_exists_and_schema():
    path = PROCESSED / "experiment_recommendations.csv"
    assert path.exists()
    experiments = pd.read_csv(path)
    assert REQUIRED.issubset(experiments.columns)
    assert not experiments.empty


def test_experiment_recommendations_fields_and_allowed_values():
    experiments = pd.read_csv(PROCESSED / "experiment_recommendations.csv")
    assert experiments["hypothesis"].notna().all()
    assert experiments["primary_metric"].notna().all()
    assert experiments["minimum_success_criteria"].notna().all()
    assert experiments["experiment_type"].isin(TYPES).all()
    assert experiments["status"].isin(STATUSES).all()
