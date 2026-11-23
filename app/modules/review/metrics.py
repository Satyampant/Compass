"""The review numbers as pure functions over plain data, and loaders that feed them.

Alignment: minutes of the day's blocks (08:00 to 20:00) that serve a goal, over all block
minutes. Meetings count as untied. A day without blocks uses its tasks' estimates instead.
Top-three completion: ranked tasks done over ranked tasks planned, dropped ones included.
Learning blocks kept: protected slots started over protected slots in the week.
Queue flow: items captured against items closed (learned, let go or expired).
Planning streak: days in a row planned before 09:00. Shutdown streak: days in a row closed.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.kernel import settings
from app.kernel.models import Event
from app.modules.day.blocks_api import day_blocks, window
from app.modules.day.models import DailyLog, Task, TimeBlock
from app.modules.learning.models import LearningItem

CLOSED_KINDS = ("item.finish", "item.let_go", "item.expire")
PLANNED_BY = time(9, 0)


# ---------- pure functions ----------


def ratio(part: float, whole: float) -> float | None:
    """part / whole, or None when there is nothing to divide."""
    return part / whole if whole else None


def alignment(spans: list[tuple[int, bool]]) -> float | None:
    """Share of minutes that serve a goal, from (minutes, tied) pairs."""
    return ratio(sum(m for m, tied in spans if tied), sum(m for m, _ in spans))


def top_three(ranked: list[bool]) -> float | None:
    """Share of ranked tasks done, from one done flag per ranked task."""
    return ratio(sum(ranked), len(ranked))


def blocks_kept(statuses: list[str]) -> tuple[int, int]:
    """Kept and total protected slots."""
    return sum(s in ("started", "kept") for s in statuses), len(statuses)


def streak(days: set[date], today: date) -> int:
    """Days in a row ending today, or ending yesterday when today is not counted yet."""
    day = today if today in days else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


# ---------- loaders ----------


@dataclass
class DayNumbers:
    aligned_min: int
    planned_min: int
    top_planned: int
    top_done: int

    @property
    def alignment(self) -> float | None:
        return ratio(self.aligned_min, self.planned_min)


def clip(block: TimeBlock, first: datetime, last: datetime) -> int:
    start, end = max(block.start, first), min(block.end, last)
    return max(int((end - start).total_seconds() // 60), 0)


def tied(session: Session, block: TimeBlock) -> bool:
    if block.task_id:
        return session.get(Task, block.task_id).goal_id is not None
    if block.item_id:
        return session.get(LearningItem, block.item_id).goal_id is not None
    return False


def day_spans(session: Session, day: date) -> list[tuple[int, bool]]:
    """(minutes, tied) for the day's blocks, or for its tasks when it has no blocks."""
    first, last = window(session, day)
    rows = [
        (clip(b, first, last), tied(session, b))
        for b in day_blocks(session, day)
        if b.status != "not_kept" and not (b.kind == "learning" and not b.item_id)
    ]
    if rows:
        return rows
    tasks = session.scalars(select(Task).where(Task.planned_date == day, Task.dropped_at.is_(None)))
    return [(t.estimate_min, t.goal_id is not None) for t in tasks]


def ranked_tasks(session: Session, first: date, last: date) -> list[bool]:
    tasks = session.scalars(
        select(Task).where(Task.planned_date.between(first, last), Task.top_rank.is_not(None))
    )
    return [t.done_at is not None for t in tasks]


def day_numbers(session: Session, day: date) -> DayNumbers:
    spans = day_spans(session, day)
    ranked = ranked_tasks(session, day, day)
    return DayNumbers(
        aligned_min=sum(m for m, t in spans if t),
        planned_min=sum(m for m, _ in spans),
        top_planned=len(ranked),
        top_done=sum(ranked),
    )


def week_slots(session: Session, monday: date) -> list[str]:
    tz = settings.tz(session)
    first = datetime.combine(monday, time(), tz)
    return list(
        session.scalars(
            select(TimeBlock.status).where(
                TimeBlock.protected.is_(True),
                TimeBlock.start >= first,
                TimeBlock.start < first + timedelta(days=7),
            )
        )
    )


def queue_flow(session: Session, first: date, last: date) -> tuple[int, int]:
    """Items captured and items closed between two local dates, from the events table."""
    tz = settings.tz(session)
    start = datetime.combine(first, time(), tz)
    end = datetime.combine(last + timedelta(days=1), time(), tz)

    def count(*kinds: str) -> int:
        return session.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.kind.in_(kinds), Event.at >= start, Event.at < end)
        )

    return count("item.captured"), count(*CLOSED_KINDS)


def planned_days(session: Session) -> set[date]:
    """Days planned before 09:00 on the day."""
    tz = settings.tz(session)
    logs = session.scalars(select(DailyLog).where(DailyLog.planned_at.is_not(None)))
    return {
        log.day
        for log in logs
        if log.planned_at.astimezone(tz) < datetime.combine(log.day, PLANNED_BY, tz)
    }


def closed_days(session: Session) -> set[date]:
    return set(session.scalars(select(DailyLog.day).where(DailyLog.closed_at.is_not(None))))
