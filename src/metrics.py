import pandas as pd
try:
    from .utils import safe_div
except ImportError:
    from utils import safe_div


HIGHER_IS_BETTER = {
    "spend": False,
    "leads": True,
    "enrollments": True,
    "net_revenue": True,
    "cac": False,
    "cpl": False,
    "roi": True,
    "roas": True,
    "ltv_cac": True,
    "activation_rate": True,
    "engagement_score": True,
    "retention_proxy": True,
    "expansion_revenue": True,
}


def calculate_cac(spend, enrollments):
    return safe_div(spend, enrollments)


def calculate_ltv_cac(expected_ltv, cac):
    return safe_div(expected_ltv, cac)


def calculate_cpl(spend, leads):
    return safe_div(spend, leads)


def calculate_roi(net_revenue, spend):
    return safe_div(net_revenue - spend, spend)


def calculate_roas(net_revenue, spend):
    return safe_div(net_revenue, spend)


def conversion_rate(numerator, denominator):
    return safe_div(numerator, denominator)


def variation_abs(actual, target):
    return float(actual or 0) - float(target or 0)


def variation_pct(actual, target):
    return safe_div(variation_abs(actual, target), target)


def status_vs_target(metric, actual, target, tolerance=0.05):
    actual = float(actual or 0)
    target = float(target or 0)
    if target == 0:
        return "baseline"
    diff = (actual - target) / target
    if abs(diff) <= tolerance:
        return "on_track"
    higher = HIGHER_IS_BETTER.get(metric, True)
    if higher:
        return "ahead" if diff > 0 else "behind"
    return "ahead" if diff < 0 else "behind"


def status_mom(metric, current, previous, tolerance=0.03):
    previous = float(previous or 0)
    current = float(current or 0)
    if previous == 0:
        return "baseline"
    diff = (current - previous) / previous
    if abs(diff) <= tolerance:
        return "estável"
    higher = HIGHER_IS_BETTER.get(metric, True)
    improved = diff > 0 if higher else diff < 0
    return "melhorou" if improved else "piorou"


def funnel_conversion(df, from_col, to_col):
    base = df[from_col].notna().sum()
    converted = df[to_col].notna().sum()
    return conversion_rate(converted, base)


def summarize_channel_performance(history):
    grouped = history.groupby("channel", as_index=False).agg(
        spend=("spend", "sum"),
        leads=("leads", "sum"),
        mqls=("mqls", "sum"),
        enrollments=("enrollments", "sum"),
        net_revenue=("net_revenue", "sum"),
        expected_ltv=("expected_ltv", "sum"),
        activation_rate=("activation_rate", "mean"),
        engagement_score=("engagement_score", "mean"),
        retention_proxy=("retention_proxy", "mean"),
        expansion_revenue=("expansion_revenue", "sum"),
    )
    grouped["cpl"] = grouped.apply(lambda r: calculate_cpl(r.spend, r.leads), axis=1)
    grouped["cac"] = grouped.apply(lambda r: calculate_cac(r.spend, r.enrollments), axis=1)
    grouped["roi"] = grouped.apply(lambda r: calculate_roi(r.net_revenue, r.spend), axis=1)
    grouped["roas"] = grouped.apply(lambda r: calculate_roas(r.net_revenue, r.spend), axis=1)
    grouped["ltv_cac"] = grouped.apply(lambda r: calculate_ltv_cac(safe_div(r.expected_ltv, r.enrollments), r.cac), axis=1)
    return grouped
