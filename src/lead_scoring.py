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
