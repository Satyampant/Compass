from datetime import UTC, date, datetime

from app.kernel import clock, settings
from app.kernel.models import Setting

PRD_RULES = [
    "resurface_days", "last_ask_day", "last_ask_grace_days", "revisit_per_day", "learning_slots",
    "learning_block_min", "default_estimate_min", "max_in_learning", "day_window",
    "capacity_weekday_hours", "capacity_weekend_hours", "capacity_week_hours", "top_priorities",
    "morning_run_time", "shutdown_nudge_time", "nudges_per_day", "pace_on_track_points",
    "pace_at_risk_points", "timezone", "week_start",
]  # fmt: skip


def test_today_changes_at_midnight_ist(session, fake_clock):
    fake_clock.set(datetime(2026, 11, 23, 18, 29, tzinfo=UTC))  # 23:59 IST
    assert settings.today(session) == date(2026, 11, 23)
    fake_clock.advance(minutes=1)  # 00:00 IST
    assert settings.today(session) == date(2026, 11, 24)


def test_every_prd_rule_has_a_default(session):
    settings.seed(session)
    session.commit()
    for key in PRD_RULES:
        assert session.get(Setting, key) is not None


def test_stored_value_overrides_default(session):
    settings.put(session, "nudges_per_day", 2)
    assert settings.get(session, "nudges_per_day") == 2


def test_week_starts_monday():
    assert clock.week_start(date(2026, 11, 29)) == date(2026, 11, 23)
