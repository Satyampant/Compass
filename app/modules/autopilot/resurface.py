"""Bring ignored inbox items back on days 3, 7 and 14, ask once more on day 21, then expire.

An item linked to a goal is a decision already made: after day 14 it waits for a learning
block and never expires.

The schedule lives on each item (next_resurface_at) and steps count by local date. After a
sleep the run replays each missed day in order, so it surfaces exactly what on-time runs would
have. A surfaced item waits on the desk until it has had one day on the revisit list. The
list holds at most revisit_per_day items: pins first, then last asks, then the oldest.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, jobs, settings
from app.modules.learning import lifecycle
from app.modules.learning.models import LearningItem

MAX_REPLAY_DAYS = 60
LAST_RUN_KEY = "autopilot.last_run_date"


def advance(session: Session, item: LearningItem, at: datetime, day_end: datetime) -> None:
    """Move one inbox item through every step due before day_end. at is the run's moment."""
    steps = settings.get(session, "resurface_days")
    last_ask_day = settings.get(session, "last_ask_day")
    grace = settings.get(session, "last_ask_grace_days")
    while item.state == "inbox" and item.next_resurface_at and item.next_resurface_at < day_end:
        n = item.resurface_count
        if n < len(steps):
            item.resurface_count = n + 1
            following = steps[n + 1] if n + 1 < len(steps) else last_ask_day
            item.next_resurface_at = item.captured_at + timedelta(days=following)
            item.surfaced_at = at
        elif item.goal_id is not None:
            item.next_resurface_at = None
        elif item.last_ask_at is None:
            item.last_ask_at = item.surfaced_at = at
            item.next_resurface_at = at + timedelta(days=grace)
        else:
            lifecycle.transition(session, item, "expire")


def _inbox(session: Session):
    return select(LearningItem).where(LearningItem.state == "inbox")


def clear_seen(session: Session, today: date) -> None:
    """Items that had their day on the list leave the desk until their next step."""
    for item in session.scalars(_inbox(session).where(LearningItem.shown_on < today)):
        item.surfaced_at = item.pinned_at = item.shown_on = None


def fill_list(session: Session, today: date) -> None:
    """Put waiting desk items on today's list, up to the daily limit."""
    limit = settings.get(session, "revisit_per_day")
    room = limit - len(todays_list(session, today))
    waiting = session.scalars(
        _inbox(session)
        .where(LearningItem.surfaced_at.is_not(None), LearningItem.shown_on.is_(None))
        .order_by(LearningItem.last_ask_at.is_(None), LearningItem.captured_at)
        .limit(max(room, 0))
    )
    for item in waiting:
        item.shown_on = today


def todays_list(session: Session, today: date) -> list[LearningItem]:
    """Today's revisit list: pins first, then last asks, then the oldest."""
    return list(
        session.scalars(
            _inbox(session)
            .where(LearningItem.shown_on == today)
            .order_by(
                LearningItem.pinned_at.is_(None),
                LearningItem.pinned_at.desc(),
                LearningItem.last_ask_at.is_(None),
                LearningItem.captured_at,
            )
            .limit(settings.get(session, "revisit_per_day"))
        )
    )


def revisit_list(session: Session) -> list[LearningItem]:
    """Today's revisit list, for the Today screen and the brief."""
    return todays_list(session, settings.today(session))


def run_day(session: Session, day: date) -> None:
    """The morning run for one local date."""
    tz = settings.tz(session)
    at = datetime.combine(day, time.fromisoformat(settings.get(session, "morning_run_time")), tz)
    day_end = datetime.combine(day + timedelta(days=1), time(), tz)
    session.flush()
    clear_seen(session, day)
    due = session.scalars(_inbox(session).where(LearningItem.next_resurface_at < day_end)).all()
    for item in due:
        advance(session, item, at, day_end)
    session.flush()
    fill_list(session, day)
    settings.put(session, LAST_RUN_KEY, day.isoformat())


def catch_up(session: Session, today: date) -> None:
    """Run every day since the last run, oldest first, ending with today."""
    last = settings.get(session, LAST_RUN_KEY)
    start = date.fromisoformat(last) + timedelta(days=1) if last else today
    start = max(start, today - timedelta(days=MAX_REPLAY_DAYS))
    day = start
    while day <= today:
        run_day(session, day)
        day += timedelta(days=1)


@jobs.handler("morning_run")
def morning_run(session: Session, payload: dict) -> None:
    """Job: resurface, expire and fill today's list, then queue the brief."""
    today = settings.today(session)
    catch_up(session, today)
    jobs.enqueue(session, "morning_brief", clock.now(), key=f"morning_brief:{today}")
