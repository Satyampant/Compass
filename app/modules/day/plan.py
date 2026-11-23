"""Plan tomorrow: one decision for each open task, then the top three. Nothing carries silently."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, events
from app.modules.day import service
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


def commit(session: Session, day: date, decisions: list[Decision], top: list[int]) -> DailyLog:
    """Apply a decision to every open task, rank the top three and mark day as planned."""
    pending = {t.id: t for t in open_tasks(session, day)}
    missing = set(pending) - {d.task_id for d in decisions}
    if missing:
        titles = ", ".join(pending[i].title for i in sorted(missing))
        raise PlanError(f"decide on every open task first: {titles}")
    for d in decisions:
        apply(session, pending.get(d.task_id), d, day)
    service.set_top(session, day, top)
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
