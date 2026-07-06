from src.metrics import calculate_cac, calculate_ltv_cac, funnel_conversion, variation_abs, variation_pct
import pandas as pd


def test_calculate_cac():
    assert calculate_cac(1000, 10) == 100
    assert calculate_cac(1000, 0) == 0


def test_calculate_ltv_cac():
    assert calculate_ltv_cac(3000, 1000) == 3
    assert calculate_ltv_cac(3000, 0) == 0


def test_funnel_conversion():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [1, None, 3]})
    assert round(funnel_conversion(df, "a", "b"), 2) == 0.67


def test_variations():
    assert variation_abs(120, 100) == 20
    assert variation_pct(120, 100) == 0.2
    assert variation_pct(120, 0) == 0
