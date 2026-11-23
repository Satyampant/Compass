"""The 23:30 day rollup: store the day's numbers, once per date."""

from datetime import date

from sqlalchemy.orm import Session

from app.kernel import clock, jobs
from app.modules.review import metrics
from app.modules.review.models import DayStats


def rollup(session: Session, day: date) -> DayStats:
    """Compute and store a day's numbers, replacing any earlier row for that date."""
    numbers = metrics.day_numbers(session, day)
    captured, closed = metrics.queue_flow(session, day, day)
    row = session.get(DayStats, day) or DayStats(day=day)
    row.aligned_min, row.planned_min = numbers.aligned_min, numbers.planned_min
    row.top_planned, row.top_done = numbers.top_planned, numbers.top_done
    row.captured, row.closed = captured, closed
    row.computed_at = clock.now()
    session.add(row)
    return row


@jobs.handler("day_rollup")
def day_rollup(session: Session, payload: dict) -> None:
    """Job: the day it was due for, even when it runs at the next wake."""
    rollup(session, date.fromisoformat(payload["day"]))
