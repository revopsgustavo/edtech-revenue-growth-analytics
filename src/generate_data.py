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
            impressions = int(spend * random.uniform(5, 14) + random.randint(250, 1200))
            clicks = int(impressions * max(0.002, np.random.normal(rule["ctr"], rule["ctr"] * 0.25)))
            leads = int(clicks * max(0.01, np.random.normal(rule["cvr"], rule["cvr"] * 0.2)))
            rows.append({
                "date": d.date(),
                "campaign_id": c.campaign_id,
                "channel": c.channel,
                "impressions": impressions,
                "clicks": clicks,
                "leads": max(0, min(leads, 24)),
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
    for lead in leads.itertuples(index=False):
        created_at = pd.Timestamp(lead.created_at)
        rule = CHANNEL_RULES[lead.channel]
        p_event = 0.58 if lead.channel in ["Free Classes / Events", "Creator-led Content", "Influencers"] else 0.34
        event_reg = maybe_date(created_at, 2, p_event)
        attendance_prob = 0.52 if pd.notna(event_reg) else 0
        if lead.channel == "Paid Social":
            attendance_prob -= 0.08
        attendance = maybe_date(event_reg, 3, attendance_prob)
        offer = maybe_date(attendance, 1, 0.88)
        mql_prob = min(0.92, (lead.lead_score / 100) * 0.95)
        mql = maybe_date(created_at, 1, mql_prob)
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
        lost = pd.NaT if enrolled else maybe_date(created_at, 12, 0.55)
        stage = "activated" if pd.notna(activation) else "enrolled" if enrolled else "lost" if pd.notna(lost) else "contacted"
        funnel_rows.append({
            "lead_id": lead.lead_id,
            "content_engagement_date": created_at - timedelta(days=random.randint(0, 4)),
            "lead_date": created_at,
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
                "touchpoint_date": created_at + timedelta(days=t * 2),
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
