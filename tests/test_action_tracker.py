from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

REQUIRED = {
    "action_id", "month", "business_area", "problem_type", "recommended_action",
    "owner", "priority", "due_date", "expected_impact", "follow_up_metric", "status",
}
PRIORITIES = {"critical", "high", "medium", "low"}
STATUSES = {"not_started", "in_progress", "done", "blocked"}


def test_action_tracker_exists_and_schema():
    path = PROCESSED / "action_tracker.csv"
    assert path.exists()
    actions = pd.read_csv(path)
    assert REQUIRED.issubset(actions.columns)
    assert not actions.empty


def test_action_tracker_fields_and_allowed_values():
    actions = pd.read_csv(PROCESSED / "action_tracker.csv")
    assert actions["owner"].notna().all()
    assert actions["follow_up_metric"].notna().all()
    assert actions["priority"].isin(PRIORITIES).all()
    assert actions["status"].isin(STATUSES).all()


def test_privacy_docs_exist():
    assert (ROOT / "docs" / "data_privacy_note.md").exists()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    production = (ROOT / "docs" / "production_flow.md").read_text(encoding="utf-8")
    assert "Aviso sobre dados e privacidade" in readme
    assert "Privacy and Governance in Production" in production
