from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def test_data_quality_report_exists():
    report = pd.read_csv(PROCESSED / "data_quality_report.csv")
    assert not report.empty
    assert {"check_name", "status", "revenue_impact"}.issubset(report.columns)


def test_no_negative_core_financial_values():
    for name in ["daily_marketing_spend.csv", "enrollments.csv", "performance_targets.csv"]:
        df = pd.read_csv(PROCESSED / name)
        nums = df.select_dtypes("number")
        nums = nums.drop(columns=[c for c in nums.columns if "roi" in c], errors="ignore")
        assert not (nums < 0).any().any()
