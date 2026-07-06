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
