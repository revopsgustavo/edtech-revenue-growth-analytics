from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DATABASE = ROOT / "data" / "database"
DOCS = ROOT / "docs"


def ensure_dirs():
    for path in [PROCESSED, DATABASE, DOCS, ROOT / "slides"]:
        path.mkdir(parents=True, exist_ok=True)


def pct(numerator, denominator):
    if denominator in (0, None) or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def safe_div(numerator, denominator):
    if denominator in (0, None) or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def brl(value):
    value = 0 if pd.isna(value) else float(value)
    return ("R$ " + f"{value:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")


def br_number(value, decimals=0):
    value = 0 if pd.isna(value) else float(value)
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def br_pct(value, decimals=1):
    return f"{br_number(float(value) * 100, decimals)}%"


def br_multiple(value, decimals=1):
    return f"{br_number(value, decimals)}x"


def save_csv(df, name):
    ensure_dirs()
    df.to_csv(PROCESSED / name, index=False, encoding="utf-8")


def read_csv(name, parse_dates=None):
    return pd.read_csv(PROCESSED / name, parse_dates=parse_dates)


def write_sqlite(tables, db_name="edtech_revenue_growth.db"):
    ensure_dirs()
    db_path = DATABASE / db_name
    with sqlite3.connect(db_path) as conn:
        for table_name, df in tables.items():
            df.to_sql(table_name, conn, index=False, if_exists="replace")
    return db_path
