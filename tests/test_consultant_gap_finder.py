from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def test_gap_log_exists_and_has_required_gaps():
    gaps = pd.read_csv(PROCESSED / "consultant_gap_log.csv")
    assert len(gaps) >= 12
    required_cols = {"gap_id", "area", "evidence", "likely_hypothesis", "validation_question", "recommended_action"}
    assert required_cols.issubset(gaps.columns)
    assert gaps["severity"].isin(["high", "medium", "low"]).all()
