"""Rules from PRD section 08 as settings with defaults, plus integration state."""

from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.kernel import clock
from app.kernel.models import Setting

DEFAULTS: dict[str, object] = {
    "resurface_days": [3, 7, 14],
    "last_ask_day": 21,
    "last_ask_grace_days": 2,
    "revisit_per_day": 3,
    "learning_slots": [
        {"weekday": 0, "time": "16:00"},
        {"weekday": 2, "time": "16:00"},
        {"weekday": 4, "time": "16:00"},
        {"weekday": 5, "time": "10:00"},
    ],
    "learning_block_min": 45,
    "default_estimate_min": 20,
    "max_in_learning": 2,
    "day_window": ["08:00", "20:00"],
    "capacity_weekday_hours": 8,
    "capacity_weekend_hours": 3,
    "capacity_week_hours": 40,
    "top_priorities": 3,
    "morning_run_time": "06:00",
    "backup_time": "05:30",
    "backup_dir": None,
    "calendar_read_ids": ["primary"],
    "calendar_name": "Compass",
    "shutdown_nudge_time": "19:30",
    "nudges_per_day": 3,
    "pace_on_track_points": 10,
    "pace_at_risk_points": 20,
    "timezone": "Asia/Kolkata",
    "week_start": "monday",
}


def get(session: Session, key: str):
    """A stored value, or its default. Unknown keys without a stored value give None."""
    row = session.get(Setting, key)
    return row.value if row else DEFAULTS.get(key)


def put(session: Session, key: str, value) -> None:
    """Store a value."""
    row = session.get(Setting, key)
    if row:
        row.value = value
    else:
        session.add(Setting(key=key, value=value))


def seed(session: Session) -> None:
    """Write every default that is not stored yet."""
    for key, value in DEFAULTS.items():
        if session.get(Setting, key) is None:
            session.add(Setting(key=key, value=value))


def tz(session: Session) -> ZoneInfo:
    """The configured time zone."""
    return ZoneInfo(get(session, "timezone"))


def today(session: Session) -> date:
    """Today's date in the configured time zone."""
    return clock.local_date(clock.now(), tz(session))
