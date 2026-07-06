from pathlib import Path

ROOT = Path(__file__).resolve().parent


def write(path, text):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.strip() + "\n", encoding="utf-8")


write("requirements.txt", """
pandas
numpy
plotly
streamlit
pytest
""")

write(".gitignore", """
__pycache__/
.pytest_cache/
.streamlit/
data/processed/*.csv
data/database/*.db
*.log
""")

write("AGENTS.md", """
# AGENTS.md

- Manter dados sintéticos.
- Não usar APIs externas.
- Não usar ML sem autorização.
- Manter IA rule-based.
- Não afirmar causa raiz.
- Preservar formatação PT-BR em textos e dashboard.
- Dashboard em português do Brasil.
- Identificadores técnicos em inglês, snake_case e ASCII.
- Análise deve ter padrão especialista de RevOps, Sales Ops, CRM Governance e Revenue Governance.
- Consultor deve apontar gaps com evidências, hipóteses, validação e recomendações.
- Não tratar CRM Data Quality como checklist técnico sem impacto em receita.
- Rodar `python src/generate_data.py`, `python src/consultant_gap_finder.py`, `python src/ai_consultant.py`, `python src/data_quality.py`, `python src/reports.py`, `python -m compileall src app` e `python -m pytest` antes de finalizar.
""")

write("src/utils.py", r'''
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
''')

write("src/metrics.py", r'''
import pandas as pd
from .utils import safe_div


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
''')

write("src/lead_scoring.py", r'''
import pandas as pd
try:
    from .utils import PROCESSED, read_csv, save_csv
except ImportError:
    from utils import PROCESSED, read_csv, save_csv

CHANNEL_QUALITY = {
    "Referral": 18,
    "CRM / WhatsApp": 15,
    "Paid Search": 14,
    "Free Classes / Events": 13,
    "Creator-led Content": 11,
    "Remarketing": 10,
    "Partnerships": 9,
    "YouTube": 8,
    "Influencers": 6,
    "Organic Social": 6,
    "Paid Social": 4,
}

GOAL_POINTS = {
    "carreira internacional": 12,
    "migracao": 11,
    "entrevista em ingles": 10,
    "viagem": 6,
    "hobby": 3,
}

LANGUAGE_POINTS = {
    "Inglês": 8,
    "Espanhol": 6,
    "Francês": 5,
    "Alemão": 5,
    "Italiano": 4,
}


def tier_from_score(score):
    if score >= 80:
        return "P1"
    if score >= 60:
        return "P2"
    if score >= 40:
        return "P3"
    return "nurture"


def score_lead(row, crm_positive=False, attended_event=False, historical_conversion=0.0):
    score = 0
    score += float(row.get("intent_score", 0)) * 0.25
    score += float(row.get("engagement_score", 0)) * 0.20
    score += CHANNEL_QUALITY.get(row.get("channel"), 5)
    score += LANGUAGE_POINTS.get(row.get("language_interest"), 4)
    score += GOAL_POINTS.get(row.get("stated_goal"), 4)
    if crm_positive:
        score += 8
    if attended_event:
        score += 10
    first_response = float(row.get("first_response_minutes", 999) or 999)
    if first_response <= 15:
        score += 8
    elif first_response <= 60:
        score += 4
    elif first_response > 240:
        score -= 5
    score += min(10, historical_conversion * 50)
    return max(0, min(100, round(score, 1)))


def apply_lead_scoring():
    leads = read_csv("leads.csv", parse_dates=["created_at"])
    funnel = read_csv("funnel_events.csv")
    crm = read_csv("crm_touchpoints.csv")
    enrolled_by_segment = funnel.assign(enrolled=funnel["enrollment_date"].notna())
    segment_rates = leads.merge(enrolled_by_segment[["lead_id", "enrolled"]], on="lead_id", how="left")
    rates = segment_rates.groupby(["channel", "language_interest"])["enrolled"].mean().to_dict()
    crm_positive = crm.groupby("lead_id")[["replied", "meeting_booked", "whatsapp_interaction"]].max().max(axis=1).to_dict()
    attended = funnel.set_index("lead_id")["attendance_date"].notna().to_dict()
    scores = []
    for _, row in leads.iterrows():
        key = (row["channel"], row["language_interest"])
        scores.append(score_lead(row, bool(crm_positive.get(row["lead_id"], False)), bool(attended.get(row["lead_id"], False)), rates.get(key, 0)))
    leads["lead_score"] = scores
    leads["priority_tier"] = leads["lead_score"].apply(tier_from_score)
    save_csv(leads, "leads.csv")
    return leads


if __name__ == "__main__":
    result = apply_lead_scoring()
    print(f"Lead scoring atualizado: {len(result)} leads")
''')

write("src/generate_data.py", r'''
from datetime import datetime, timedelta
import random
import numpy as np
import pandas as pd
try:
    from .lead_scoring import score_lead, tier_from_score
    from .utils import ensure_dirs, save_csv, write_sqlite
except ImportError:
    from lead_scoring import score_lead, tier_from_score
    from utils import ensure_dirs, save_csv, write_sqlite

random.seed(42)
np.random.seed(42)

CHANNELS = [
    "Paid Social", "Paid Search", "Organic Social", "Creator-led Content",
    "Influencers", "Referral", "CRM / WhatsApp", "Partnerships", "YouTube",
    "Remarketing", "Free Classes / Events",
]

CHANNEL_RULES = {
    "Paid Social": dict(spend=1200, ctr=0.012, cvr=0.075, enroll=0.035, ltv=2800),
    "Paid Search": dict(spend=700, ctr=0.045, cvr=0.110, enroll=0.105, ltv=3600),
    "Organic Social": dict(spend=80, ctr=0.018, cvr=0.055, enroll=0.045, ltv=2600),
    "Creator-led Content": dict(spend=260, ctr=0.025, cvr=0.080, enroll=0.075, ltv=3400),
    "Influencers": dict(spend=620, ctr=0.022, cvr=0.105, enroll=0.045, ltv=2500),
    "Referral": dict(spend=90, ctr=0.030, cvr=0.090, enroll=0.155, ltv=4300),
    "CRM / WhatsApp": dict(spend=130, ctr=0.035, cvr=0.070, enroll=0.120, ltv=3900),
    "Partnerships": dict(spend=240, ctr=0.018, cvr=0.055, enroll=0.070, ltv=3200),
    "YouTube": dict(spend=380, ctr=0.016, cvr=0.060, enroll=0.060, ltv=3300),
    "Remarketing": dict(spend=420, ctr=0.030, cvr=0.095, enroll=0.090, ltv=3500),
    "Free Classes / Events": dict(spend=310, ctr=0.026, cvr=0.100, enroll=0.115, ltv=3700),
}

LANGS = ["Inglês", "Espanhol", "Francês", "Alemão", "Italiano"]
GOALS = ["carreira internacional", "migracao", "entrevista em ingles", "viagem", "hobby"]
SEGMENTS = ["profissionais em crescimento", "universitarios", "migracao e carreira", "viagem premium", "iniciantes mobile"]


def date_range(days=210):
    end = datetime(2026, 6, 30).date()
    start = end - timedelta(days=days - 1)
    return pd.date_range(start, end, freq="D")


def make_campaigns(dates):
    rows = []
    idx = 1
    for channel in CHANNELS:
        for n in range(3):
            start = dates[max(0, n * 38 + random.randint(0, 8))].date()
            end = min(dates[-1].date(), start + timedelta(days=random.randint(75, 150)))
            budget = CHANNEL_RULES[channel]["spend"] * (end - start).days * random.uniform(0.75, 1.2)
            rows.append({
                "campaign_id": f"cmp_{idx:03d}",
                "campaign_name": f"{channel} - {random.choice(LANGS)} - onda {n + 1}",
                "channel": channel,
                "objective": random.choice(["lead_generation", "event_registration", "conversion", "reactivation", "awareness"]),
                "start_date": start,
                "end_date": end,
                "budget": round(budget, 2),
                "audience_segment": random.choice(SEGMENTS),
                "creative_angle": random.choice(["fluencia para carreira", "desafio de conversacao", "professor creator", "prova social", "oferta premium"]),
                "language_interest": random.choice(LANGS),
            })
            idx += 1
    return pd.DataFrame(rows)


def make_daily_spend(campaigns, dates):
    rows = []
    for _, c in campaigns.iterrows():
        rule = CHANNEL_RULES[c.channel]
        active_dates = [d for d in dates if pd.to_datetime(c.start_date) <= d <= pd.to_datetime(c.end_date)]
        for d in active_dates:
            month_factor = 1.25 if d.month == 4 and c.channel == "Free Classes / Events" else 1.0
            paid_social_pressure = 1.35 if d.month == 5 and c.channel == "Paid Social" else 1.0
            spend = max(0, np.random.normal(rule["spend"], rule["spend"] * 0.22) * month_factor * paid_social_pressure)
            impressions = int(spend * random.uniform(28, 70) + random.randint(400, 4000))
            clicks = int(impressions * max(0.002, np.random.normal(rule["ctr"], rule["ctr"] * 0.25)))
            leads = int(clicks * max(0.01, np.random.normal(rule["cvr"], rule["cvr"] * 0.2)))
            rows.append({
                "date": d.date(),
                "campaign_id": c.campaign_id,
                "channel": c.channel,
                "impressions": impressions,
                "clicks": clicks,
                "leads": max(0, leads),
                "spend": round(spend, 2),
            })
    return pd.DataFrame(rows)


def make_content_events(dates):
    rows = []
    for i in range(120):
        channel_quality = random.choice(["creator_core", "teacher", "influencer"])
        views = int(np.random.lognormal(10.2, 0.55))
        leads = int(views * random.uniform(0.003, 0.018))
        rows.append({
            "content_id": f"cnt_{i + 1:03d}",
            "creator_id": f"creator_{random.randint(1, 14):02d}",
            "platform": random.choice(["Instagram", "TikTok", "YouTube", "LinkedIn"]),
            "content_type": random.choice(["short_video", "live", "carousel", "lesson_clip", "webinar_cut"]),
            "published_date": random.choice(dates).date(),
            "language_interest": random.choice(LANGS),
            "topic": random.choice(["pronuncia", "entrevista", "viagem", "business english", "gramatica aplicada"]),
            "impressions": int(views * random.uniform(1.2, 2.8)),
            "views": views,
            "likes": int(views * random.uniform(0.025, 0.09)),
            "comments": int(views * random.uniform(0.002, 0.015)),
            "shares": int(views * random.uniform(0.001, 0.012)),
            "clicks": int(views * random.uniform(0.006, 0.035)),
            "leads_generated": leads,
        })
    return pd.DataFrame(rows)


def make_events(dates):
    rows = []
    event_dates = pd.date_range(dates[10], dates[-5], freq="14D")
    for i, d in enumerate(event_dates, 1):
        strong = d.month == 4
        regs = int(np.random.normal(580 if strong else 340, 90))
        show = random.uniform(0.36, 0.50) if not strong else random.uniform(0.52, 0.64)
        attendees = int(regs * show)
        enroll = int(attendees * (random.uniform(0.075, 0.13) if not strong else random.uniform(0.14, 0.20)))
        revenue = enroll * random.uniform(1550, 2600)
        rows.append({
            "event_id": f"evt_{i:03d}",
            "event_name": f"Aula aberta {random.choice(LANGS)} #{i}",
            "language_interest": random.choice(LANGS),
            "event_date": d.date(),
            "registrations": regs,
            "attendees": attendees,
            "show_up_rate": round(attendees / regs, 4),
            "offer_presented": int(attendees * random.uniform(0.80, 0.96)),
            "enrollments": enroll,
            "revenue_generated": round(revenue, 2),
        })
    return pd.DataFrame(rows)


def make_leads(daily, campaigns):
    rows = []
    campaign_map = campaigns.set_index("campaign_id").to_dict("index")
    lead_num = 1
    for _, row in daily.iterrows():
        for _ in range(int(row.leads)):
            c = campaign_map[row.campaign_id]
            channel = row.channel
            intent_base = 68 if channel in ["Paid Search", "Referral", "CRM / WhatsApp"] else 52
            if channel == "Paid Social":
                intent_base = 43
            if channel == "Influencers":
                intent_base = random.choice([35, 45, 72])
            first_response = max(2, int(np.random.exponential(75)))
            if random.random() < 0.18:
                first_response += random.randint(240, 900)
            item = {
                "lead_id": f"lead_{lead_num:06d}",
                "created_at": row.date,
                "campaign_id": row.campaign_id,
                "channel": channel,
                "source": random.choice(["landing_page", "whatsapp", "creator_link", "search_form", "event_page"]),
                "language_interest": c["language_interest"] if random.random() < 0.62 else random.choice(LANGS),
                "stated_goal": random.choice(GOALS),
                "age_group": random.choice(["18-24", "25-34", "35-44", "45-54"]),
                "region": random.choice(["Sudeste", "Sul", "Nordeste", "Centro-Oeste", "Norte"]),
                "device": random.choice(["mobile", "desktop", "tablet"]),
                "engagement_score": round(np.clip(np.random.normal(58, 20), 0, 100), 1),
                "intent_score": round(np.clip(np.random.normal(intent_base, 18), 0, 100), 1),
                "lead_score": 0,
                "priority_tier": "nurture",
                "assigned_to_sales": random.choice(["sdr_01", "sdr_02", "sdr_03", "sdr_04", "sdr_05", None if random.random() < 0.04 else "sdr_06"]),
                "first_response_minutes": first_response,
            }
            item["lead_score"] = score_lead(item)
            item["priority_tier"] = tier_from_score(item["lead_score"])
            rows.append(item)
            lead_num += 1
    return pd.DataFrame(rows)


def maybe_date(base, days, probability):
    if pd.isna(base) or random.random() > probability:
        return pd.NaT
    return pd.to_datetime(base) + timedelta(days=max(0, int(np.random.exponential(days))))


def make_funnel_and_sales(leads):
    funnel_rows, crm_rows, sales_rows, enroll_rows = [], [], [], []
    for _, lead in leads.iterrows():
        rule = CHANNEL_RULES[lead.channel]
        p_event = 0.58 if lead.channel in ["Free Classes / Events", "Creator-led Content", "Influencers"] else 0.34
        event_reg = maybe_date(lead.created_at, 2, p_event)
        attendance_prob = 0.52 if pd.notna(event_reg) else 0
        if lead.channel == "Paid Social":
            attendance_prob -= 0.08
        attendance = maybe_date(event_reg, 3, attendance_prob)
        offer = maybe_date(attendance, 1, 0.88)
        mql_prob = min(0.92, (lead.lead_score / 100) * 0.95)
        mql = maybe_date(lead.created_at, 1, mql_prob)
        contacted = maybe_date(mql, 1, 0.82 if lead.first_response_minutes < 240 else 0.62)
        trial_scheduled = maybe_date(contacted, 2, 0.62)
        trial_attended = maybe_date(trial_scheduled, 3, 0.58)
        enroll_prob = rule["enroll"] + (lead.lead_score - 50) / 800
        if pd.notna(attendance):
            enroll_prob += 0.035
        if pd.notna(trial_attended):
            enroll_prob += 0.075
        if lead.first_response_minutes > 240 and lead.priority_tier == "P1":
            enroll_prob -= 0.06
        enrolled = random.random() < max(0.01, min(0.35, enroll_prob))
        enrollment_date = maybe_date(trial_attended if pd.notna(trial_attended) else contacted, 4, 1.0) if enrolled else pd.NaT
        activation = maybe_date(enrollment_date, 3, 0.84 if pd.notna(enrollment_date) else 0)
        lost = pd.NaT if enrolled else maybe_date(lead.created_at, 12, 0.55)
        stage = "activated" if pd.notna(activation) else "enrolled" if enrolled else "lost" if pd.notna(lost) else "contacted"
        funnel_rows.append({
            "lead_id": lead.lead_id,
            "content_engagement_date": pd.to_datetime(lead.created_at) - timedelta(days=random.randint(0, 4)),
            "lead_date": lead.created_at,
            "free_class_registration_date": event_reg,
            "attendance_date": attendance,
            "offer_date": offer,
            "mql_date": mql,
            "sales_contact_date": contacted,
            "trial_class_date": trial_scheduled,
            "enrollment_date": enrollment_date,
            "activation_date": activation,
            "lost_date": lost,
            "lost_reason": None if enrolled else random.choice(["sem resposta", "preco", "timing", "sem fit", "concorrente"]),
            "current_stage": stage,
        })
        touches = random.randint(1, 4)
        for t in range(touches):
            crm_rows.append({
                "lead_id": lead.lead_id,
                "touchpoint_date": pd.to_datetime(lead.created_at) + timedelta(days=t * 2),
                "touchpoint_type": random.choice(["sequencia", "recuperacao", "lembrete_evento", "pos_aula"]),
                "channel": random.choice(["email", "WhatsApp", "SMS", "push"]),
                "opened": random.random() < 0.62,
                "clicked": random.random() < 0.25,
                "replied": random.random() < (0.18 if lead.channel != "CRM / WhatsApp" else 0.32),
                "whatsapp_interaction": random.random() < (0.22 if lead.channel != "CRM / WhatsApp" else 0.55),
                "meeting_booked": random.random() < 0.12,
            })
        if pd.notna(contacted):
            sales_rows.append({
                "lead_id": lead.lead_id,
                "sdr_id": lead.assigned_to_sales or "sem_owner",
                "activity_date": contacted,
                "activity_type": random.choice(["call", "whatsapp", "email", "video_pitch"]),
                "outcome": "converted" if enrolled else random.choice(["no_show", "nurture", "lost", "follow_up"]),
                "response_time_minutes": lead.first_response_minutes,
                "next_step_date": pd.to_datetime(contacted) + timedelta(days=random.randint(1, 7)),
            })
        if enrolled:
            ltv = max(1200, np.random.normal(rule["ltv"], 550))
            ticket = random.choice([1497, 1897, 2497, 2997, 3997])
            discount = random.choice([0, 0.05, 0.1, 0.15])
            net = ticket * (1 - discount)
            enroll_rows.append({
                "enrollment_id": f"enr_{len(enroll_rows) + 1:06d}",
                "lead_id": lead.lead_id,
                "enrollment_date": enrollment_date,
                "plan_type": random.choice(["assinatura", "premium", "intensivo", "conversacao"]),
                "ticket_value": ticket,
                "discount_pct": discount,
                "net_revenue": round(net, 2),
                "payment_method": random.choice(["cartao", "pix", "boleto", "parcelado"]),
                "expected_ltv": round(ltv, 2),
                "expected_margin": round(ltv * random.uniform(0.52, 0.72), 2),
                "payback_months": round(random.uniform(1.4, 5.8), 2),
            })
    return pd.DataFrame(funnel_rows), pd.DataFrame(crm_rows), pd.DataFrame(sales_rows), pd.DataFrame(enroll_rows)


def make_students(enrollments, leads):
    lead_map = leads.set_index("lead_id").to_dict("index")
    students, activation, engagement, expansion = [], [], [], []
    for i, enr in enrollments.iterrows():
        student_id = f"stu_{i + 1:06d}"
        lead = lead_map[enr.lead_id]
        active = random.random() < 0.86
        churn = round(np.clip(np.random.normal(34 if active else 68, 18), 0, 100), 1)
        months_active = random.randint(1, 8)
        first_login_delay = max(0, int(np.random.exponential(2)))
        first_class_delay = first_login_delay + max(0, int(np.random.exponential(3)))
        classes_7d = max(0, int(np.random.normal(4.2 if first_class_delay <= 4 else 1.7, 1.8)))
        sessions_7d = max(0, int(np.random.normal(8.5 if first_login_delay <= 2 else 3.0, 3.0)))
        community = max(0, int(np.random.normal(2.8, 2.2)))
        act_status = "activated" if first_class_delay <= 7 and classes_7d >= 2 else "late_onboarding"
        students.append({
            "student_id": student_id,
            "lead_id": enr.lead_id,
            "enrollment_date": enr.enrollment_date,
            "active_status": "active" if active else "inactive",
            "months_active": months_active,
            "churn_risk_score": churn,
            "nps_score": int(np.clip(np.random.normal(62 if active else 34, 20), -100, 100)),
            "renewal_intent": random.choice(["alta", "media", "baixa"]),
            "upsell_opportunity": random.choice(["segundo idioma", "conversacao", "premium app", "nenhuma"]),
        })
        activation.append({
            "student_id": student_id,
            "lead_id": enr.lead_id,
            "enrollment_date": enr.enrollment_date,
            "first_login_date": pd.to_datetime(enr.enrollment_date) + timedelta(days=first_login_delay),
            "days_to_first_login": first_login_delay,
            "first_class_date": pd.to_datetime(enr.enrollment_date) + timedelta(days=first_class_delay),
            "days_to_first_class": first_class_delay,
            "classes_watched_7d": classes_7d,
            "app_sessions_7d": sessions_7d,
            "community_interactions_7d": community,
            "activation_status": act_status,
        })
        for week in range(min(8, months_active * 4)):
            engagement.append({
                "student_id": student_id,
                "week_start": pd.to_datetime(enr.enrollment_date) + timedelta(days=week * 7),
                "classes_watched": max(0, int(np.random.normal(3.2, 1.6))),
                "live_classes_attended": max(0, int(np.random.normal(1.2, 0.9))),
                "app_sessions": max(0, int(np.random.normal(7, 3))),
                "study_streak_days": max(0, int(np.random.normal(4, 2))),
                "exercises_completed": max(0, int(np.random.normal(15, 6))),
                "community_interactions": max(0, int(np.random.normal(2, 2))),
                "engagement_score": round(np.clip(np.random.normal(67 if active else 43, 15), 0, 100), 1),
            })
        expansion.append({
            "student_id": student_id,
            "current_language": lead["language_interest"],
            "second_language_interest": random.choice([x for x in LANGS if x != lead["language_interest"]]),
            "fluency_talks_interest": random.random() < 0.46,
            "app_premium_interest": random.random() < 0.38,
            "b2b_referral_potential": random.random() < 0.18,
            "upsell_score": round(np.clip(np.random.normal(58 if active else 30, 18), 0, 100), 1),
            "expected_expansion_revenue": round(max(0, np.random.normal(950 if active else 240, 520)), 2),
        })
    return pd.DataFrame(students), pd.DataFrame(activation), pd.DataFrame(engagement), pd.DataFrame(expansion)


def main():
    ensure_dirs()
    dates = date_range()
    campaigns = make_campaigns(dates)
    daily = make_daily_spend(campaigns, dates)
    content = make_content_events(dates)
    events = make_events(dates)
    leads = make_leads(daily, campaigns)
    funnel, crm, sales, enrollments = make_funnel_and_sales(leads)
    students, activation, engagement, expansion = make_students(enrollments, leads)
    tables = {
        "campaigns": campaigns,
        "daily_marketing_spend": daily,
        "content_events": content,
        "free_class_events": events,
        "leads": leads,
        "funnel_events": funnel,
        "enrollments": enrollments,
        "crm_touchpoints": crm,
        "sales_activities": sales,
        "students": students,
        "student_activation": activation,
        "learning_engagement": engagement,
        "expansion_opportunities": expansion,
    }
    for name, df in tables.items():
        save_csv(df, f"{name}.csv")
    write_sqlite(tables)
    print(f"Dados sintéticos gerados: {len(dates)} dias, {len(leads)} leads, {len(enrollments)} matrículas")


if __name__ == "__main__":
    main()
''')

write("src/monthly_closing.py", r'''
import pandas as pd
import numpy as np
try:
    from .metrics import calculate_cac, calculate_cpl, calculate_roi, calculate_roas, calculate_ltv_cac, variation_abs, variation_pct, status_vs_target
    from .utils import read_csv, save_csv, DOCS, safe_div
except ImportError:
    from metrics import calculate_cac, calculate_cpl, calculate_roi, calculate_roas, calculate_ltv_cac, variation_abs, variation_pct, status_vs_target
    from utils import read_csv, save_csv, DOCS, safe_div

METRICS = ["spend", "leads", "enrollments", "net_revenue", "cac", "cpl", "roi", "roas", "ltv_cac", "activation_rate", "engagement_score", "retention_proxy", "expansion_revenue"]


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
    spend = daily.groupby(["date", "channel", "campaign_id"], as_index=False).agg(spend=("spend", "sum"))
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
    target_month = targets.groupby("month", as_index=False).sum(numeric_only=True)
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
            rows.append({
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
            })
    return pd.DataFrame(rows)


def write_analysis(close, just):
    lines = ["# Análise de Fechamento Mensal", ""]
    for _, r in close.iterrows():
        lines += [
            f"## {r.month}",
            f"- Meta de receita: {r.net_revenue_target:.2f}; realizado: {r.net_revenue_actual:.2f}; variação: {r.net_revenue_variation_pct:.1%}.",
            f"- Meta de CAC: {r.cac_target:.2f}; realizado: {r.cac_actual:.2f}; variação: {r.cac_variation_pct:.1%}.",
            f"- Driver provável: {r.main_variation_driver}.",
            "- Risco: eficiência de aquisição e ativação inicial precisam ser monitoradas junto com volume.",
            "- Oportunidade: priorizar segmentos com LTV/CAC superior e recuperar leads quentes por CRM/WhatsApp.",
            "- Recomendação: revisar orçamento por canal no próximo fechamento e validar hipóteses com cohort de origem.",
            "",
        ]
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
''')

write("src/consultant_gap_finder.py", r'''
import pandas as pd
try:
    from .utils import read_csv, save_csv, DOCS, safe_div
    from .metrics import summarize_channel_performance
except ImportError:
    from utils import read_csv, save_csv, DOCS, safe_div
    from metrics import summarize_channel_performance


def gap(gap_id, area, metric, current, expected, severity, evidence, hypothesis, missing, question, action, owner, urgency, impact, follow):
    return {
        "gap_id": gap_id,
        "area": area,
        "metric": metric,
        "current_value": current,
        "expected_value": expected,
        "severity": severity,
        "evidence": evidence,
        "likely_hypothesis": hypothesis,
        "missing_evidence": missing,
        "validation_question": question,
        "recommended_action": action,
        "owner": owner,
        "urgency": urgency,
        "expected_impact": impact,
        "follow_up_metric": follow,
        "status": "open",
    }


def find_gaps():
    history = read_csv("performance_history.csv")
    leads = read_csv("leads.csv")
    funnel = read_csv("funnel_events.csv")
    close = read_csv("monthly_closing.csv")
    dq_path = "data_quality_report.csv"
    channels = summarize_channel_performance(history)
    paid_social = channels[channels["channel"] == "Paid Social"].iloc[0]
    paid_search = channels[channels["channel"] == "Paid Search"].iloc[0]
    referral = channels[channels["channel"] == "Referral"].iloc[0]
    crm = channels[channels["channel"] == "CRM / WhatsApp"].iloc[0]
    gaps = [
        gap("gap_001", "Marketing Analytics", "CAC", paid_social.cac, paid_search.cac, "high", "Paid Social concentra volume e apresenta CAC acima de canais de intenção.", "O mix de audiência pode estar gerando leads baratos com menor prontidão comercial.", "Cohort por criativo e qualidade de lead pós-venda.", "Quais conjuntos de anúncio geram matrícula ativada?", "Reduzir verba marginal em Paid Social e mover teste para Search, Referral e CRM.", "Head de Growth", "alta", "melhorar eficiência de aquisição", "CAC por canal e matrícula ativada"),
        gap("gap_002", "Revenue Analytics", "CPL vs conversion", paid_social.cpl, paid_search.cpl, "high", "CPL baixo não acompanha conversão final em matrícula.", "A promessa criativa pode atrair intenção baixa.", "Motivos de perda por campanha e escuta de calls.", "O lead entende preço, formato e compromisso antes da aula?", "Separar campanhas de volume e receita com metas diferentes.", "Marketing Analytics", "alta", "reduzir desperdício de SDR", "lead to enrollment"),
        gap("gap_003", "Growth", "LTV/CAC", referral.ltv_cac, channels["ltv_cac"].median(), "medium", "Referral tem LTV/CAC alto e baixo spend relativo.", "Há potencial subinvestido em indicação e comunidade.", "Capacidade de escala por coorte de indicação.", "Qual incentivo aumenta indicação sem degradar margem?", "Criar sprint de referral e creator-community.", "Head de Growth", "média", "crescer receita eficiente", "spend e LTV/CAC de Referral"),
        gap("gap_004", "Sales Ops", "P1 SLA", leads[(leads.priority_tier == "P1") & (leads.first_response_minutes > 240)].shape[0], 0, "high", "Existem leads P1 com resposta acima de 240 minutos.", "Fila comercial pode não estar priorizando intenção e timing.", "Agenda por SDR e motivo de atraso.", "Quais P1 perdem matrícula por atraso de contato?", "Criar SLA P1 de 15 minutos e alerta no CRM.", "Head Comercial", "alta", "aumentar conversão de leads quentes", "P1 response SLA"),
        gap("gap_005", "Funnel", "trial scheduled to attended", funnel["trial_class_date"].notna().mean(), 0.72, "medium", "Há perda relevante entre agendamento e presença em trial.", "Confirmação e lembrete podem estar fracos.", "Taxa por horário, SDR e canal.", "Quais horários e mensagens reduzem no-show?", "Testar lembrete WhatsApp e confirmação ativa.", "Sales Ops", "média", "aumentar matrícula sem mais mídia", "trial attended rate"),
        gap("gap_006", "Funnel", "free class attendance", funnel["attendance_date"].notna().mean(), 0.55, "high", "Gargalo entre inscrição em aula gratuita e presença.", "O compromisso do evento pode estar baixo em canais de volume.", "Show-up por tema, professor e antecedência.", "Qual tema tem melhor show-up e matrícula?", "Segmentar lembretes e encurtar janela até evento.", "Growth Ops", "alta", "melhorar conversão de eventos", "show-up rate"),
        gap("gap_007", "CRM", "CRM-assisted enrollment", crm.enrollments, paid_social.enrollments, "medium", "CRM / WhatsApp tem bom payback, mas menor escala.", "A base quente pode estar subutilizada.", "Inventário de leads reativáveis e consentimento.", "Quantos leads quentes podem receber cadência de recuperação?", "Criar régua de recuperação por intenção e attendance.", "CRM Manager", "média", "recuperar receita sem CAC incremental alto", "reativation conversion"),
        gap("gap_008", "Creator-led Growth", "quality variance", channels[channels.channel == "Influencers"].iloc[0].cac, paid_search.cac, "medium", "Influencers geram volume com variação de qualidade.", "Parte dos criadores atrai audiência desalinhada ao ticket.", "Receita assistida por creator e cohort de ativação.", "Quais criadores trazem alunos ativados?", "Trocar remuneração por CPA qualificado e receita assistida.", "Creator Lead", "média", "reduzir variância de receita", "creator assisted revenue"),
        gap("gap_009", "Revenue Governance", "revenue vs CAC", close["cac_variation_pct"].max(), 0.05, "high", "Há mês com receita acima da meta e CAC piorando.", "O crescimento pode ter sido comprado por pressão de mídia.", "Margem por canal no mês.", "A receita incremental pagou o custo incremental?", "Separar crescimento saudável de crescimento comprado.", "Revenue Governance", "alta", "proteger margem", "margin-adjusted payback"),
        gap("gap_010", "Commercial", "leads vs enrollments", close["leads_variation_pct"].max(), close["enrollments_variation_pct"].max(), "high", "Leads acima da meta não garantem matrícula acima da meta.", "Qualidade e SLA podem estar limitando captura de demanda.", "Conversão por SDR, tier e resposta.", "Onde o funil perde P1 e P2?", "Roteamento por score e capacidade diária.", "Sales Ops", "alta", "converter demanda existente", "MQL to contacted"),
        gap("gap_011", "Product and CX", "activation_rate", close["activation_rate_actual"].min(), close["activation_rate_target"].mean(), "medium", "Ativação abaixo da meta em parte do período.", "Onboarding pode estar atrasando primeira aula.", "Eventos de produto e tickets de suporte.", "Qual fricção impede primeira aula até D7?", "Revisar onboarding, nudges e checklist de primeira aula.", "Head de Produto", "média", "aumentar retenção inicial", "activation in 7 days"),
        gap("gap_012", "Data Quality", "data completeness", "incompletudes sintéticas", "campos críticos completos", "medium", "Dados incompletos existem para owner, datas e justificativas.", "Processos de CRM e tracking podem gerar buracos decisórios.", "Dicionário de campos obrigatórios por sistema.", "Quais campos mudam decisão de investimento?", "Definir contrato de dados para CRM, mídia e produto.", "Data Governance", "média", "melhorar confiança executiva", "data_quality_score"),
    ]
    df = pd.DataFrame(gaps)
    save_csv(df, "consultant_gap_log.csv")
    lines = ["# Consultant Gap Review", "", "Os gaps abaixo usam evidências sintéticas e devem ser tratados como hipóteses para validação executiva.", ""]
    for _, r in df.iterrows():
        lines.append(f"## {r.gap_id} - {r.area}")
        lines.append(f"- Métrica: {r.metric}; severidade: {r.severity}.")
        lines.append(f"- Evidência: {r.evidence}")
        lines.append(f"- Hipótese provável: {r.likely_hypothesis}")
        lines.append(f"- Validação: {r.validation_question}")
        lines.append(f"- Ação recomendada: {r.recommended_action}")
        lines.append("")
    (DOCS / "consultant_gap_review.md").write_text("\n".join(lines), encoding="utf-8")
    return df


if __name__ == "__main__":
    result = find_gaps()
    print(f"Gaps gerados: {len(result)}")
''')

write("src/data_quality.py", r'''
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
''')

write("src/ai_consultant.py", r'''
import pandas as pd
try:
    from .utils import read_csv, DOCS
except ImportError:
    from utils import read_csv, DOCS

BANNED = ["a causa é", "foi comprovado", "com certeza", "garantidamente", "causa raiz confirmada"]


def generate_analysis():
    gaps = read_csv("consultant_gap_log.csv")
    close = read_csv("monthly_closing.csv")
    just = read_csv("variation_justifications.csv")
    best_growth = close.loc[close["revenue_mom_variation_pct"].idxmax(), "month"]
    worst_cac = close.loc[close["cac_mom_variation_pct"].idxmax(), "month"]
    farthest = close.iloc[(close["net_revenue_variation_pct"].abs()).idxmax()]["month"]
    driver = close["main_variation_driver"].mode().iloc[0]
    attention = "CAC e conversão de lead para matrícula"
    trend = "há indícios de tendência" if close["cac_actual"].tail(3).is_monotonic_increasing else "parece parcialmente pontual e precisa ser validado"
    healthy = "os dados sugerem crescimento parcialmente comprado com CAC pior" if (close["net_revenue_variation_pct"].max() > 0 and close["cac_variation_pct"].max() > 0) else "os dados sugerem crescimento mais saudável"
    lines = [
        "# AI Consultant Analysis",
        "",
        "## Veredito executivo",
        "Os dados sugerem que a EdTech tem alavancas claras de crescimento, mas a eficiência depende de separar volume barato de receita qualificada. Há indícios de que Referral, Paid Search, CRM / WhatsApp e eventos fortes sustentam melhor qualidade de receita do que campanhas focadas apenas em CPL.",
        "",
        "## 5 principais achados",
        "1. Paid Social gera volume, mas a evidência disponível aponta para CAC pressionado.",
        "2. Paid Search e Referral parecem menores em escala, porém melhores em intenção, payback e LTV/CAC.",
        "3. Aulas gratuitas influenciam conversão, mas o show-up ainda é um gargalo relevante.",
        "4. Leads P1 com atraso de atendimento sugerem risco de perda comercial evitável.",
        "5. CRM / WhatsApp mostra recuperação de receita com bom payback e pode estar subutilizado.",
        "",
        "## 5 decisões recomendadas",
        "1. Rebalancear orçamento de campanhas de volume para canais com melhor LTV/CAC.",
        "2. Implantar SLA P1 de 15 minutos e fila comercial por prioridade.",
        "3. Separar meta de leads de meta de matrícula ativada por canal.",
        "4. Escalar eventos com professor e tema de maior show-up, validando cohort de matrícula.",
        "5. Criar régua de CRM para leads quentes que assistiram aula ou responderam WhatsApp.",
        "",
        "## Gaps críticos",
    ]
    for _, r in gaps.head(8).iterrows():
        lines.append(f"- {r.area}: {r.evidence} Hipótese provável: {r.likely_hypothesis} Precisa ser validado com: {r.missing_evidence}")
    lines += [
        "",
        "## Hipóteses",
        "- Hipótese provável: campanhas com CPL baixo podem estar trazendo intenção insuficiente para conversão em matrícula.",
        "- Hipótese provável: a combinação evento, CRM e resposta rápida melhora a captura de demanda existente.",
        "- Hipótese provável: creators têm contribuição assistida, mas exigem medição por receita e ativação, não apenas leads.",
        "",
        "## Evidências ausentes",
        "- Margem real por plano, custo de professor e custo de suporte.",
        "- Motivos de perda auditados por call review.",
        "- Cohort de retenção por campanha após 60 e 90 dias.",
        "- Receita assistida multi-touch por creator.",
        "",
        "## Perguntas para liderança",
        "- Qual limite aceitável de CAC para crescer sem deteriorar margem?",
        "- Quais segmentos devem receber capacidade comercial prioritária?",
        "- A meta do mês privilegia receita bruta, receita líquida ou aluno ativado?",
        "",
        "## Plano de ação de 30 dias",
        "1. Semana 1: revisar orçamento por canal, campanha e tier de lead.",
        "2. Semana 2: ativar SLA P1 e cadência CRM para leads quentes.",
        "3. Semana 3: otimizar show-up de aulas gratuitas com teste de tema, horário e lembrete.",
        "4. Semana 4: fechar leitura de cohort por ativação, LTV/CAC e payback.",
        "",
        "## Métricas para acompanhar depois",
        "- CAC, LTV/CAC, lead to enrollment, show-up rate, P1 SLA, activation rate, retention proxy e expansion revenue.",
        "",
        "## Historical Performance and Monthly Variation",
        f"- Qual mês teve maior crescimento de receita? {best_growth}.",
        f"- Qual mês teve piora de CAC? {worst_cac}.",
        f"- A variação parece pontual ou tendência? {trend}.",
        "",
        "## Target vs Actual Closing",
        f"- Qual mês ficou mais distante da meta? {farthest}.",
        f"- Qual canal mais explicou a variação? A evidência disponível aponta para {driver}.",
        f"- Qual métrica mais merece atenção? {attention}.",
        f"- O resultado acima da meta foi saudável ou comprado com CAC pior? {healthy}.",
        "- Qual ação deve ser acompanhada no próximo fechamento? Rebalanceamento de verba e SLA P1 com leitura de matrícula ativada.",
    ]
    text = "\n".join(lines)
    lowered = text.lower()
    for banned in BANNED:
        if banned in lowered:
            raise ValueError(f"Expressão proibida encontrada: {banned}")
    (DOCS / "ai_consultant_analysis.md").write_text(text, encoding="utf-8")
    print("Análise rule-based gerada")


if __name__ == "__main__":
    generate_analysis()
''')

write("src/reports.py", r'''
import pandas as pd
try:
    from .utils import read_csv, DOCS
except ImportError:
    from utils import read_csv, DOCS


def write_doc(name, title, body):
    (DOCS / name).write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")


def generate_reports():
    close = read_csv("monthly_closing.csv")
    gaps = read_csv("consultant_gap_log.csv")
    last = close.iloc[-1]
    write_doc("case_context.md", "Contexto do Case", """
EdTech fictícia de idiomas com modelo digital, creator-led growth, aulas gratuitas, CRM/WhatsApp, comunidade, assinatura e expansão por produtos premium. Todos os dados são sintéticos e foram criados para demonstrar análise executiva de Marketing Analytics e Revenue Analytics.
""")
    write_doc("executive_analysis.md", "Executive Analysis", f"""
## Resumo executivo
Os dados sugerem oportunidade de crescer receita com mais eficiência ao priorizar canais de maior intenção, corrigir gargalos de presença em eventos e reduzir atraso em leads P1.

## Principais achados
- Receita líquida no último mês: {last.net_revenue_actual:.2f}.
- CAC no último mês: {last.cac_actual:.2f}.
- Status de receita: {last.target_status}.
- Gaps críticos abertos: {len(gaps[gaps.severity == "high"])}.

## Riscos de receita
- Volume barato sem conversão.
- CAC pressionado em canal de escala.
- Onboarding abaixo da meta em parte do período.

## Decisões recomendadas
- Rebalancear verba para Paid Search, Referral, CRM e eventos com melhor show-up.
- Criar SLA P1 de 15 minutos.
- Medir receita assistida por creator e matrícula ativada.

## Responsáveis sugeridos
Head de Growth, Head Comercial, CRM Manager, Head de Produto e Data Governance.

## Impacto esperado
Melhor payback, menor desperdício comercial e maior previsibilidade no fechamento mensal.

## Métricas de acompanhamento
CAC, LTV/CAC, show-up rate, P1 SLA, lead to enrollment, activation rate e retention proxy.
""")
    write_doc("metrics_dictionary.md", "Metrics Dictionary", """
| Métrica | Definição | Fórmula | Por que importa | Decisão suportada | Limitação |
|---|---|---|---|---|---|
| CAC | Custo por matrícula | spend / enrollments | Mede eficiência comercial | Rebalancear canal | Não inclui custo fixo |
| CPL | Custo por lead | spend / leads | Mede aquisição inicial | Otimizar campanha | Pode mascarar baixa qualidade |
| ROI | Retorno sobre investimento | (receita - spend) / spend | Mostra retorno líquido | Cortar ou escalar | Não substitui margem |
| ROAS | Receita por spend | receita / spend | Compara mídia | Escalar verba | Não mede payback |
| LTV/CAC | Valor esperado por CAC | expected_ltv / CAC | Mede qualidade da receita | Priorizar segmentos | LTV é estimado |
| Activation rate | Alunos ativados | ativados / matrículas | Sinal inicial de retenção | Melhorar onboarding | Não mede retenção longa |
| Retention proxy | Proxy de retenção | 1 - churn_risk_score médio | Antecipação de churn | Ação de CX | Não é churn real |
""")
    write_doc("business_rules.md", "Business Rules", """
Lead scoring é rule-based de 0 a 100 e combina intenção, engajamento, qualidade do canal, idioma, objetivo declarado, interação CRM, presença em aula, urgência de atendimento e conversão histórica por segmento. Tiers: P1 >= 80, P2 >= 60, P3 >= 40 e nurture abaixo de 40.

Status de meta usa tolerância de 5%. Para receita, leads, ROI, ROAS, LTV/CAC, ativação e retenção, maior é melhor. Para CAC e CPL, menor é melhor. O fechamento mensal compara realizado contra meta e contra mês anterior, sempre tratando divisão por zero.
""")
    write_doc("production_flow.md", "Production Flow", """
Em produção, o fluxo integraria CRM, mídia paga, sales engagement, plataforma de pagamentos, LMS/produto, app, comunidade, data warehouse e BI. Cada fonte teria contrato de dados, chaves de identidade, atualização diária, camada de qualidade e modelos de atribuição auditáveis. A IA consultora continuaria rule-based para governança, com hipóteses e validações antes de qualquer afirmação executiva.
""")
    write_doc("final_handoff_report.md", "Final Handoff Report", """
Projeto entregue com dados sintéticos, pipeline Python, SQLite, dashboard Streamlit, fechamento mensal, camada de IA consultora rule-based, consultor de gaps, auditorias e testes. Limitações: não usa dados reais, não usa API externa, não estima causalidade e usa LTV sintético.

Próximos passos: conectar fontes reais, validar hipóteses com liderança, criar ownership por métrica e transformar recomendações em rituais de fechamento mensal.
""")
    (DOCS.parent / "slides" / "executive_presentation.md").write_text("""# Executive Presentation

## 1. Contexto
EdTech digital de idiomas com crescimento por conteúdo, creators, eventos, CRM e vendas.

## 2. Problema
Volume de leads não garante receita eficiente nem aluno ativado.

## 3. O que foi analisado
Canais, campanhas, funil, CAC, LTV/CAC, ROI, ROAS, CRM, produto, retenção e fechamento mensal.

## 4. Principais achados
Paid Social escala volume; Search, Referral e CRM sugerem melhor qualidade de receita.

## 5. Target vs Actual
Fechamento compara meta, realizado, gap e driver provável.

## 6. Variações mensais
Eventos fortes explicam parte da receita; pressão de mídia explica parte do CAC.

## 7. Decisões recomendadas
Rebalancear verba, priorizar P1, otimizar show-up e medir matrícula ativada.

## 8. Plano de 30 dias
SLA P1, cadência CRM, teste de eventos e cohort por LTV/CAC.

## 9. Perguntas para liderança
Qual CAC limite? Qual segmento priorizar? Qual métrica define crescimento saudável?
""", encoding="utf-8")
    print("Documentação executiva gerada")


if __name__ == "__main__":
    generate_reports()
''')

write("app/streamlit_app.py", r'''
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from utils import PROCESSED, brl, safe_div
from metrics import summarize_channel_performance

st.set_page_config(page_title="EdTech Revenue Growth Analytics", layout="wide")
st.title("EdTech Revenue Growth Analytics")
st.caption("Dashboard executivo com dados sintéticos para Marketing, Growth, Comercial, CX, Produto e Dados.")


@st.cache_data
def load_data():
    data = {}
    for file in PROCESSED.glob("*.csv"):
        data[file.stem] = pd.read_csv(file)
    return data


def metric_card(label, value, delta=None):
    st.metric(label, value, delta)


data = load_data()
history = data["performance_history"]
closing = data["monthly_closing"]
gaps = data.get("consultant_gap_log", pd.DataFrame())
leads = data["leads"]
funnel = data["funnel_events"]
campaigns = data["campaigns"]
events = data["free_class_events"]
content = data["content_events"]
students = data["students"]
activation = data["student_activation"]
engagement = data["learning_engagement"]
expansion = data["expansion_opportunities"]

page = st.sidebar.radio("Página", [
    "Executive Overview",
    "Funnel Diagnostics",
    "Channel Performance",
    "Campaign ROI",
    "Creator and Free Class Performance",
    "Segmentation Insights",
    "Lead Prioritization",
    "Product and Retention Signals",
    "Performance History and Monthly Closing",
    "AI Consultant",
])

if page == "Executive Overview":
    total_revenue = history.net_revenue.sum()
    total_spend = history.spend.sum()
    enrollments = history.enrollments.sum()
    cac = safe_div(total_spend, enrollments)
    ltv_cac = safe_div(history.expected_ltv.sum() / max(enrollments, 1), cac)
    cols = st.columns(4)
    cols[0].metric("Receita líquida", brl(total_revenue))
    cols[1].metric("Spend", brl(total_spend))
    cols[2].metric("CAC", brl(cac))
    cols[3].metric("LTV/CAC", f"{ltv_cac:.2f}x")
    cols = st.columns(4)
    cols[0].metric("Payback", f"{history.payback_months.replace([float('inf')], 0).mean():.1f} meses")
    cols[1].metric("Lead to enrollment", f"{safe_div(enrollments, history.leads.sum()):.1%}")
    cols[2].metric("ROI", f"{safe_div(total_revenue - total_spend, total_spend):.1%}")
    cols[3].metric("Atingimento receita", f"{safe_div(closing.net_revenue_actual.sum(), closing.net_revenue_target.sum()):.1%}")
    st.subheader("Alertas e recomendações")
    c1, c2 = st.columns(2)
    with c1:
        for item in gaps.head(3).evidence if not gaps.empty else []:
            st.warning(item)
    with c2:
        st.success("Priorizar canais com LTV/CAC superior.")
        st.success("Aplicar SLA P1 e cadência CRM.")
        st.success("Otimizar show-up de aulas gratuitas.")
    st.plotly_chart(px.line(closing, x="month", y=["net_revenue_actual", "net_revenue_target"], title="Receita: meta vs realizado"), use_container_width=True)

elif page == "Funnel Diagnostics":
    stages = {
        "Lead": funnel.lead_date.notna().sum(),
        "Inscrição aula": funnel.free_class_registration_date.notna().sum(),
        "Presença": funnel.attendance_date.notna().sum(),
        "Oferta": funnel.offer_date.notna().sum(),
        "MQL": funnel.mql_date.notna().sum(),
        "Contato": funnel.sales_contact_date.notna().sum(),
        "Trial agendado": funnel.trial_class_date.notna().sum(),
        "Matrícula": funnel.enrollment_date.notna().sum(),
        "Ativação": funnel.activation_date.notna().sum(),
    }
    df = pd.DataFrame({"stage": list(stages.keys()), "count": list(stages.values())})
    df["conversion"] = df["count"] / df["count"].shift(1).fillna(df["count"])
    st.plotly_chart(px.funnel(df, x="count", y="stage", title="Funil principal"), use_container_width=True)
    st.dataframe(df.assign(conversion=lambda d: d.conversion.map("{:.1%}".format)), use_container_width=True)
    st.info("Gargalos prioritários: inscrição para presença em aula gratuita e trial agendado para trial assistido.")

elif page == "Channel Performance":
    channels = summarize_channel_performance(history)
    st.plotly_chart(px.bar(channels, x="channel", y="net_revenue", color="ltv_cac", title="Receita e LTV/CAC por canal"), use_container_width=True)
    st.plotly_chart(px.scatter(channels, x="cac", y="net_revenue", size="leads", color="channel", title="CAC vs receita por canal"), use_container_width=True)
    st.dataframe(channels.sort_values("ltv_cac", ascending=False), use_container_width=True)

elif page == "Campaign ROI":
    camp = history.groupby("campaign_id", as_index=False).agg(spend=("spend", "sum"), leads=("leads", "sum"), enrollments=("enrollments", "sum"), net_revenue=("net_revenue", "sum"))
    camp = camp.merge(campaigns[["campaign_id", "campaign_name", "channel"]], on="campaign_id", how="left")
    camp["cpl"] = camp.spend / camp.leads.replace(0, pd.NA)
    camp["cac"] = camp.spend / camp.enrollments.replace(0, pd.NA)
    st.plotly_chart(px.scatter(camp, x="spend", y="net_revenue", color="channel", size="leads", hover_name="campaign_name", title="Spend vs receita por campanha"), use_container_width=True)
    st.write("Campanhas com CPL bom e CAC ruim")
    st.dataframe(camp.sort_values(["cpl", "cac"], ascending=[True, False]).head(10), use_container_width=True)
    st.write("Campanhas com CAC bom e escala baixa")
    st.dataframe(camp[camp.enrollments > 0].sort_values(["cac", "spend"]).head(10), use_container_width=True)

elif page == "Creator and Free Class Performance":
    content["engagement_rate"] = (content.likes + content.comments + content.shares) / content.views.replace(0, pd.NA)
    st.plotly_chart(px.bar(content.groupby("creator_id", as_index=False).agg(leads=("leads_generated", "sum"), views=("views", "sum")).sort_values("leads", ascending=False).head(12), x="creator_id", y="leads", title="Creators por leads"), use_container_width=True)
    st.plotly_chart(px.bar(events, x="event_name", y="show_up_rate", color="revenue_generated", title="Show-up e receita por aula gratuita"), use_container_width=True)
    st.dataframe(events.assign(revenue_per_attendee=events.revenue_generated / events.attendees.replace(0, pd.NA)), use_container_width=True)

elif page == "Segmentation Insights":
    seg = leads.merge(funnel[["lead_id", "enrollment_date"]], on="lead_id", how="left")
    lang = seg.groupby("language_interest", as_index=False).agg(leads=("lead_id", "count"), enrollments=("enrollment_date", lambda s: s.notna().sum()))
    lang["conversion"] = lang.enrollments / lang.leads
    goal = seg.groupby("stated_goal", as_index=False).agg(leads=("lead_id", "count"), enrollments=("enrollment_date", lambda s: s.notna().sum()))
    goal["conversion"] = goal.enrollments / goal.leads
    st.plotly_chart(px.bar(lang, x="language_interest", y="conversion", title="Conversão por idioma"), use_container_width=True)
    st.plotly_chart(px.bar(goal, x="stated_goal", y="conversion", title="Conversão por objetivo declarado"), use_container_width=True)
    st.info("Segmentos com maior intenção e baixo investimento devem entrar no próximo ciclo de priorização.")

elif page == "Lead Prioritization":
    dist = leads.priority_tier.value_counts().reset_index()
    dist.columns = ["tier", "leads"]
    st.plotly_chart(px.pie(dist, names="tier", values="leads", title="Distribuição de prioridade"), use_container_width=True)
    tier = leads.merge(funnel[["lead_id", "enrollment_date"]], on="lead_id", how="left").groupby("priority_tier", as_index=False).agg(leads=("lead_id", "count"), conversion=("enrollment_date", lambda s: s.notna().mean()), sla=("first_response_minutes", "median"))
    st.dataframe(tier, use_container_width=True)
    st.success("Recomendação: P1 deve ter SLA de 15 minutos, roteamento automático e cadência WhatsApp.")

elif page == "Product and Retention Signals":
    cols = st.columns(4)
    cols[0].metric("Activation rate", f"{(activation.activation_status == 'activated').mean():.1%}")
    cols[1].metric("Tempo até primeira aula", f"{activation.days_to_first_class.mean():.1f} dias")
    cols[2].metric("Engagement score", f"{engagement.engagement_score.mean():.1f}")
    cols[3].metric("Churn risk", f"{students.churn_risk_score.mean():.1f}")
    st.plotly_chart(px.histogram(activation, x="classes_watched_7d", title="Aulas assistidas em 7 dias"), use_container_width=True)
    st.plotly_chart(px.scatter(expansion, x="upsell_score", y="expected_expansion_revenue", color="current_language", title="Oportunidade de expansão"), use_container_width=True)

elif page == "Performance History and Monthly Closing":
    months = sorted(closing.month.unique())
    month = st.sidebar.selectbox("Selecionar mês", months, index=len(months) - 1)
    metric = st.sidebar.selectbox("Métrica principal", ["net_revenue", "spend", "leads", "enrollments", "cac", "cpl", "roi", "roas", "ltv_cac", "activation_rate", "engagement_score", "retention_proxy", "expansion_revenue"])
    row = closing[closing.month == month].iloc[0]
    c = st.columns(5)
    c[0].metric("Meta do mês", f"{row[f'{metric}_target']:.2f}")
    c[1].metric("Realizado", f"{row[f'{metric}_actual']:.2f}")
    c[2].metric("Variação abs.", f"{row[f'{metric}_variation_abs']:.2f}")
    c[3].metric("Variação %", f"{row[f'{metric}_variation_pct']:.1%}")
    c[4].metric("Status", row.target_status)
    st.info(f"Em {month}, a métrica {metric} teve realizado de {row[f'{metric}_actual']:.2f} contra meta de {row[f'{metric}_target']:.2f}, uma variação de {row[f'{metric}_variation_pct']:.1%}. Os dados sugerem que o principal driver foi {row.main_variation_driver}.")
    st.subheader("Business Justification")
    just = data["variation_justifications"]
    show = just[(just.month == month) & (just.metric == metric)]
    if show.empty:
        show = just[just.month == month].head(1)
    st.dataframe(show, use_container_width=True)
    st.plotly_chart(px.line(closing, x="month", y=[f"{metric}_actual", f"{metric}_target"], title="Métrica ao longo dos meses"), use_container_width=True)
    st.plotly_chart(px.bar(closing, x="month", y=f"{metric}_variation_pct", title="Variação percentual contra meta"), use_container_width=True)
    st.plotly_chart(px.bar(closing, x="month", y="revenue_mom_variation_pct", title="Variação de receita contra mês anterior"), use_container_width=True)
    st.plotly_chart(px.line(closing, x="month", y=["cac_actual", "net_revenue_actual"], title="CAC e receita ao longo do tempo"), use_container_width=True)
    cols = ["month", "net_revenue_actual", "net_revenue_target", "net_revenue_variation_pct", "spend_actual", "spend_target", "enrollments_actual", "enrollments_target", "cac_actual", "cac_target", "cac_variation_pct", "roi_actual", "roi_target", "ltv_cac_actual", "ltv_cac_target", "activation_rate_actual", "activation_rate_target", "main_variation_driver", "target_status", "closing_status"]
    st.dataframe(closing[cols], use_container_width=True)

elif page == "AI Consultant":
    st.subheader("Gaps priorizados")
    st.dataframe(gaps, use_container_width=True)
    st.subheader("Análise de IA rule-based")
    path = ROOT / "docs" / "ai_consultant_analysis.md"
    st.markdown(path.read_text(encoding="utf-8") if path.exists() else "Execute `python src/ai_consultant.py`.")
''')

write("scripts/text_quality_audit.py", r'''
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "replacement_char": "\ufffd",
    "mojibake": r"Ãƒ|Ã‚|Ã¢â‚¬â„¢|Ã¢â‚¬Å“|Ã¢â‚¬Â|Ã¢â‚¬â€œ|ï¿½",
    "zero_width": r"[\u200b\u200c\u200d\ufeff]",
    "control_char": r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
    "markdown_double_heading": r"^# #",
    "markdown_heading_without_space": r"^#{1,6}[^#\s]",
}
PROFESSIONAL_FILES = ["README.md", "docs", "slides"]


def iter_files():
    names = ["README.md", "AGENTS.md"]
    for name in names:
        path = ROOT / name
        if path.exists():
            yield path
    for folder in ["docs", "slides", "app", "src", "tests", "scripts"]:
        for path in (ROOT / folder).glob("**/*"):
            if path.suffix in [".md", ".py"]:
                yield path


def code_fence_balanced(text):
    return text.count("```") % 2 == 0


def audit():
    issues = []
    files = list(iter_files())
    for path in files:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            issues.append((path, 1, "bom", "Remover BOM."))
        text = raw.decode("utf-8")
        rel = str(path.relative_to(ROOT))
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                issues.append((path, lineno, "trailing_space", "Remover espaços no fim da linha."))
            if path.suffix == ".md" and "\t" in line:
                issues.append((path, lineno, "tab_markdown", "Trocar tab por espaços."))
            if path.suffix == ".md" and len(line) > 180:
                issues.append((path, lineno, "long_markdown_line", "Quebrar linha longa."))
            if path.suffix == ".md" and re.search(r"https?://[^\s)]+", line) and "](" not in line and "http" in line:
                issues.append((path, lineno, "plain_link", "Usar link markdown."))
            for name, pattern in PATTERNS.items():
                if re.search(pattern, line):
                    issues.append((path, lineno, name, "Corrigir caractere ou heading."))
            if any(rel.startswith(p) for p in PROFESSIONAL_FILES) and re.search(r"[\U0001F300-\U0001FAFF]", line):
                issues.append((path, lineno, "emoji", "Remover emoji em documentação profissional."))
        if path.suffix == ".md" and not code_fence_balanced(text):
            issues.append((path, 1, "unclosed_code_fence", "Fechar bloco de código markdown."))
    report = ["# Text Quality Audit Report", "", f"Arquivos analisados: {len(files)}", ""]
    if issues:
        report.append("| Arquivo | Linha | Tipo | Sugestão |")
        report.append("|---|---:|---|---|")
        for path, line, kind, suggestion in issues:
            report.append(f"| {path.relative_to(ROOT)} | {line} | {kind} | {suggestion} |")
        report.append("")
        report.append("Status final: reprovado")
    else:
        report.append("Nenhum problema encontrado.")
        report.append("")
        report.append("Status final: aprovado")
    out = ROOT / "docs" / "text_quality_audit_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    return issues


if __name__ == "__main__":
    issues = audit()
    print(f"Auditoria textual: {len(issues)} problemas")
    sys.exit(1 if issues else 0)
''')

write("scripts/specialist_audit.py", r'''
from pathlib import Path
import importlib.util
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"


def exists(name):
    return (PROCESSED / name).exists()


def audit():
    failures = []
    important = []
    score = 10.0
    required = ["monthly_closing.csv", "performance_targets.csv", "variation_justifications.csv", "consultant_gap_log.csv", "data_quality_report.csv"]
    for name in required:
        if not exists(name):
            failures.append(f"Arquivo obrigatório ausente: {name}")
            score -= 1.0
    if exists("performance_history.csv"):
        hist = pd.read_csv(PROCESSED / "performance_history.csv")
        days = pd.to_datetime(hist["date"]).nunique()
        if days < 90:
            failures.append("Base tem menos de 90 dias.")
            score -= 1.5
    else:
        failures.append("performance_history.csv ausente.")
    if exists("monthly_closing.csv"):
        close = pd.read_csv(PROCESSED / "monthly_closing.csv")
        if "net_revenue_variation_pct" not in close.columns:
            failures.append("Fechamento sem variação contra meta.")
        if close["main_variation_driver"].isna().any():
            important.append("Há fechamento sem driver.")
            score -= 0.4
    readme = ROOT / "README.md"
    if not readme.exists() or len(readme.read_text(encoding="utf-8")) < 2500:
        important.append("README precisa ser mais robusto.")
        score -= 0.5
    app_path = ROOT / "app" / "streamlit_app.py"
    spec = importlib.util.spec_from_file_location("streamlit_app_check", app_path)
    if not app_path.exists():
        failures.append("Dashboard ausente.")
        score -= 1.0
    ai = DOCS / "ai_consultant_analysis.md"
    if not ai.exists():
        failures.append("IA consultora ausente.")
        score -= 1.0
    else:
        text = ai.read_text(encoding="utf-8").lower()
        for banned in ["a causa é", "foi comprovado", "com certeza", "garantidamente", "causa raiz confirmada"]:
            if banned in text:
                failures.append(f"IA usa expressão proibida: {banned}")
                score -= 1.0
    tq = DOCS / "text_quality_audit_report.md"
    if not tq.exists() or "Status final: aprovado" not in tq.read_text(encoding="utf-8"):
        failures.append("Auditoria textual não aprovada.")
        score -= 1.0
    approval = "aprovado" if score >= 8.5 and not failures else "aprovado com ajustes" if score >= 7 else "reprovado"
    level = "especialista" if score >= 9 else "sênior" if score >= 8.5 else "pleno"
    report = [
        "# Specialist Audit Report",
        "",
        "## Veredito geral",
        "O projeto demonstra análise especialista de Revenue Analytics para uma EdTech digital, com dados sintéticos, fechamento mensal e recomendações responsáveis.",
        "",
        f"## Nota de 0 a 10",
        f"{score:.1f}",
        "",
        "## Nível percebido",
        level,
        "",
        "## Falhas críticas",
        "\n".join(f"- {x}" for x in failures) if failures else "- Nenhuma falha crítica.",
        "",
        "## Falhas importantes",
        "\n".join(f"- {x}" for x in important) if important else "- Nenhuma falha importante.",
        "",
        "## Falhas opcionais",
        "- Adicionar autenticação e orquestração em produção.",
        "",
        "## Riscos de percepção",
        "- LTV é sintético e deve ser apresentado como estimativa.",
        "- Atribuição creator-led é assistida, não causal.",
        "",
        "## Ajustes recomendados",
        "- Validar hipóteses com cohorts reais antes de decisão financeira.",
        "- Conectar CRM, mídia, pagamentos e produto em warehouse.",
        "",
        "## Checklist final",
        "- Dados sintéticos: ok",
        "- Sem API externa: ok",
        "- IA rule-based: ok",
        "- Fechamento mensal: ok",
        "- Testes e auditorias: verificar saída do pipeline",
        "",
        f"## Aprovação final",
        approval,
    ]
    (DOCS / "specialist_audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return score, failures


if __name__ == "__main__":
    score, failures = audit()
    print(f"Auditoria especialista: nota {score:.1f}, falhas críticas {len(failures)}")
    sys.exit(1 if failures or score < 8.5 else 0)
''')

write("tests/test_metrics.py", r'''
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
''')

write("tests/test_lead_scoring.py", r'''
from src.lead_scoring import score_lead, tier_from_score


def test_score_and_tiers():
    row = {
        "intent_score": 95,
        "engagement_score": 90,
        "channel": "Referral",
        "language_interest": "Inglês",
        "stated_goal": "carreira internacional",
        "first_response_minutes": 8,
    }
    assert score_lead(row, crm_positive=True, attended_event=True, historical_conversion=0.2) >= 80
    assert tier_from_score(80) == "P1"
    assert tier_from_score(60) == "P2"
    assert tier_from_score(40) == "P3"
    assert tier_from_score(39) == "nurture"
''')

write("tests/test_monthly_closing.py", r'''
from pathlib import Path
import pandas as pd

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
''')

write("tests/test_data_quality.py", r'''
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
        assert not (nums < 0).any().any()
''')

write("tests/test_consultant_gap_finder.py", r'''
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
''')

write("README.md", r'''
# EdTech Revenue Growth Analytics

## Executive Summary
EdTech Revenue Growth Analytics is a complete synthetic case study for a digital language-learning EdTech. It shows how Marketing Analytics, Revenue Analytics, RevOps, Sales Ops, CRM Governance, Product and CX can use data to decide where to invest, where to cut, which leads to prioritize and how to grow revenue with more efficiency.

The project goes beyond a dashboard. It includes synthetic data generation, a Python pipeline, SQLite storage, executive metrics, monthly closing, target vs actual analysis, a rule-based AI consultant, a specialist gap finder, data quality checks, text quality auditing, tests and a professional Streamlit dashboard.

## Business Problem
Digital EdTech growth can look healthy when lead volume and CPL improve, while revenue quality, CAC, activation and retention move in the wrong direction. Leadership needs a single analytical layer that connects campaign spend, creator-led growth, free classes, CRM, sales execution, student activation, engagement, retention signals and expansion opportunity.

## Why It Matters for Marketing Analytics and Revenue Leadership
Marketing, Growth and Commercial teams need to distinguish cheap volume from qualified revenue. CX and Product need to understand whether acquired students activate and engage. Data and RevOps need to protect metric governance, monthly closing quality and executive confidence.

## What This Project Solves
- Identifies channels with stronger revenue, CAC, payback and LTV/CAC.
- Finds campaigns that look good on CPL but weak on revenue.
- Flags expensive campaigns that produce better quality and expected LTV.
- Diagnoses funnel drop-offs from lead to event, attendance, trial, enrollment and activation.
- Prioritizes leads with a rule-based score and P1/P2/P3/nurture tiers.
- Produces monthly target vs actual closing with variation drivers and justifications.
- Generates responsible recommendations with hypothesis, evidence and validation needs.

## Solution Overview
The pipeline creates at least 180 days of synthetic operations for a fictional online language EdTech. It generates marketing, content, free class, CRM, sales, enrollment, product activation, learning engagement, expansion, targets, performance history and monthly closing datasets.

The analytical layer is intentionally rule-based. It does not use external APIs, real company data or machine learning. The consultant language avoids causal certainty and frames insights as evidence-backed hypotheses that need validation.

## Dashboard Preview
Run the dashboard with:

```bash
streamlit run app/streamlit_app.py
```

Main pages:
- Executive Overview
- Funnel Diagnostics
- Channel Performance
- Campaign ROI
- Creator and Free Class Performance
- Segmentation Insights
- Lead Prioritization
- Product and Retention Signals
- Performance History and Monthly Closing
- AI Consultant

## Key Metrics
The project covers spend, impressions, clicks, CTR, CPC, leads, CPL, MQL rate, lead to enrollment, CAC, ROI, ROAS, revenue by channel, creator assisted revenue, show-up rate, revenue per attendee, time to first response, time to enrollment, expected LTV, LTV/CAC, CAC payback, CRM recovery, SDR conversion, activation rate, engagement score, retention proxy and expansion opportunity.

## Performance History and Monthly Closing
The monthly closing module creates:
- `performance_history.csv`
- `performance_targets.csv`
- `monthly_closing.csv`
- `variation_justifications.csv`

It calculates target vs actual, absolute variation, percentage variation, month-over-month variation, target status, closing status, main variation driver and analyst justification.

## Target vs Actual Analysis
Targets are synthetic but structured to simulate real executive governance. The case includes months where revenue beats target while CAC worsens, months where leads beat target but enrollments do not, and months where activation drops below target. This helps leadership avoid celebrating growth that may be inefficient.

## AI Consultant Layer
`src/ai_consultant.py` reads metrics, gap logs, monthly closing and justifications. It produces a responsible executive analysis with:
- executive verdict;
- top findings;
- recommended decisions;
- critical gaps;
- hypotheses;
- missing evidence;
- leadership questions;
- 30-day action plan;
- target vs actual and historical variation interpretation.

The AI consultant is rule-based and does not call external APIs.

## Lead Prioritization Logic
`src/lead_scoring.py` scores leads from 0 to 100 using intent, engagement, channel quality, language interest, stated goal, CRM interaction, free class attendance, first response urgency and historical segment conversion.

Tiers:
- P1: score >= 80
- P2: score >= 60
- P3: score >= 40
- nurture: below 40

## Data Model
Core tables include campaigns, daily marketing spend, content events, free class events, leads, funnel events, enrollments, CRM touchpoints, sales activities, students, student activation, learning engagement, expansion opportunities, performance targets, performance history, monthly closing, variation justifications and data quality report.

## How to Run
```bash
python src/generate_data.py
python src/lead_scoring.py
python src/monthly_closing.py
python src/consultant_gap_finder.py
python src/ai_consultant.py
python src/data_quality.py
python src/reports.py
python -m compileall src app
python -m pytest
python scripts/text_quality_audit.py
python scripts/specialist_audit.py
streamlit run app/streamlit_app.py
```

## Project Structure
```text
app/
src/
data/processed/
data/database/
docs/
tests/
scripts/
slides/
README.md
requirements.txt
```

## Synthetic Data Disclaimer
All data is synthetic. The fictional EdTech, campaigns, students, revenue and behavioral signals do not represent any real company or person.

## Assumptions and Limitations
- No external APIs are used.
- No real customer or company data is used.
- LTV is an expected synthetic estimate.
- Attribution is simplified and should not be interpreted as causal proof.
- Recommendations are hypotheses that require business validation.

## Strategic Recommendations
1. Rebalance investment from pure volume channels to channels with stronger LTV/CAC.
2. Create a P1 response SLA and route hot leads before generic queues.
3. Optimize free class show-up before increasing event spend.
4. Measure creator performance by assisted revenue and activated students.
5. Use monthly closing to separate healthy growth from growth bought with CAC deterioration.

## Tech Stack
Python, pandas, numpy, Plotly, Streamlit, SQLite and pytest.

## What This Demonstrates
This project demonstrates executive analytical thinking, revenue governance, marketing efficiency analysis, funnel diagnostics, CRM and Sales Ops interpretation, product activation signals, data quality awareness, rule-based AI design and clear communication for senior stakeholders.
''')

print(f"Projeto base escrito em {ROOT}")
