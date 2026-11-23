"""Plan tomorrow: one decision for each open task, then the top three. Nothing carries silently."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, events, settings
from app.modules.day import blocks, blocks_api, service
from app.modules.day.models import DailyLog, Task

ACTIONS = ("tomorrow", "reschedule", "drop")


class PlanError(ValueError):
    """A plan that leaves an open task undecided or decides one wrongly."""


@dataclass
class Decision:
    task_id: int
    action: str
    to: date | None = None


def open_tasks(session: Session, day: date) -> list[Task]:
    """Tasks before day that are neither done nor dropped."""
    return list(
        session.scalars(
            select(Task)
            .where(Task.planned_date < day, Task.done_at.is_(None), Task.dropped_at.is_(None))
            .order_by(Task.planned_date, Task.created_at)
        )
    )


def planned(session: Session, day: date) -> list[Task]:
    """Tasks already on day, not dropped."""
    return list(
        session.scalars(
            select(Task)
            .where(Task.planned_date == day, Task.dropped_at.is_(None))
            .order_by(Task.top_rank.is_(None), Task.top_rank, Task.created_at)
        )
    )


def commit(
    session: Session,
    day: date,
    decisions: list[Decision],
    top: list[int],
    placements: list["Placement"] | None = None,
) -> DailyLog:
    """Apply a decision to every open task, rank the top three, place the blocks and mark the
    day as planned. Without placements the day's blocks are left as they are."""
    pending = {t.id: t for t in open_tasks(session, day)}
    missing = set(pending) - {d.task_id for d in decisions}
    if missing:
        titles = ", ".join(pending[i].title for i in sorted(missing))
        raise PlanError(f"decide on every open task first: {titles}")
    for d in decisions:
        apply(session, pending.get(d.task_id), d, day)
    service.set_top(session, day, top)
    if placements is not None:
        place_blocks(session, day, placements)
    log = session.get(DailyLog, day) or DailyLog(day=day)
    log.planned_at = clock.now()
    session.add(log)
    events.record(session, "day.planned", "day", None, day=day.isoformat())
    return log


def apply(session: Session, task: Task | None, d: Decision, day: date) -> None:
    """Move a task to day, to another date, or drop it."""
    if task is None:
        raise PlanError(f"task {d.task_id} is not an open task")
    if d.action not in ACTIONS:
        raise PlanError(f"action must be one of {ACTIONS}")
    if d.action == "reschedule" and (d.to is None or d.to < day):
        raise PlanError("reschedule needs a date from the planned day on")
    task.top_rank = None
    if d.action == "drop":
        task.dropped_at = clock.now()
    else:
        task.planned_date = day if d.action == "tomorrow" else d.to
    task.version += 1
    events.record(session, f"task.{d.action}", "task", task.id)


@dataclass
class Placement:
    task_id: int
    start: datetime
    end: datetime


NOON = time(13, 0)
STEP = timedelta(minutes=15)


def gaps(busy: list[tuple[datetime, datetime]], first: datetime, last: datetime):
    """Free stretches between busy spans inside the window."""
    out, at = [], first
    for start, end in sorted(busy):
        if start > at:
            out.append((at, min(start, last)))
        at = max(at, end)
    if at < last:
        out.append((at, last))
    return [(s, e) for s, e in out if e > s]


def round_up(at: datetime) -> datetime:
    """The next quarter hour."""
    minutes = (at.minute + 14) // 15 * 15
    return at.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)


def propose(session: Session, day: date, task_ids: list[int]) -> list[Placement]:
    """Blocks for tasks in order: the first into the longest free morning gap, the rest into
    the earliest gap they fit, all around meetings and the learning slot."""
    first, last = blocks_api.window(session, day)
    busy = [
        (b.start, b.end)
        for b in blocks_api.day_blocks(session, day)
        if b.kind != "task" and b.status != "not_kept"
    ]
    tz = settings.tz(session)
    placed = []
    for n, task_id in enumerate(task_ids):
        task = session.get(Task, task_id)
        need = timedelta(minutes=task.estimate_min)
        free = [(round_up(s), e) for s, e in gaps(busy, first, last)]
        fits = [(s, e) for s, e in free if e - s >= need]
        if not fits:
            continue
        if n == 0:
            morning = [g for g in fits if g[0].astimezone(tz).time() < NOON] or fits
            start = max(morning, key=lambda g: g[1] - g[0])[0]
        else:
            start = fits[0][0]
        placed.append(Placement(task_id, start, start + need))
        busy.append((start, start + need))
    return placed


def place_blocks(session: Session, day: date, placements: list[Placement]) -> None:
    """Replace the day's task blocks with the confirmed placements."""
    for block in blocks_api.day_blocks(session, day):
        if block.kind == "task" and block.source == "compass":
            blocks.remove(session, block)
    for p in placements:
        task = session.get(Task, p.task_id)
        blocks.create(session, "task", p.start, p.end, task.title, task_id=task.id)
