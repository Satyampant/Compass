"""Learning slot times from settings."""

from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from app.kernel import settings


def next_slot(session: Session, after: datetime) -> datetime:
    """The start of the next protected learning slot after a moment."""
    tz = settings.tz(session)
    local = after.astimezone(tz)
    starts = []
    for slot in settings.get(session, "learning_slots"):
        days_ahead = (slot["weekday"] - local.weekday()) % 7
        for extra in (0, 7):
            day = local.date() + timedelta(days=days_ahead + extra)
            start = datetime.combine(day, time.fromisoformat(slot["time"]), tz)
            if start > after:
                starts.append(start)
                break
    return min(starts)
