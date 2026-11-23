"""Tasks for a day."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, events
from app.modules.day.models import Task


def create_task(
    session: Session,
    title: str,
    planned_date: date,
    estimate_min: int = 30,
    goal_id: int | None = None,
) -> Task:
    """Add a task to a day, tied to a goal or untied."""
    task = Task(
        title=title,
        planned_date=planned_date,
        estimate_min=estimate_min,
        goal_id=goal_id,
        created_at=clock.now(),
    )
    session.add(task)
    session.flush()
    events.record(session, "task.created", "task", task.id)
    return task


def set_top(session: Session, day: date, task_ids: list[int]) -> list[Task]:
    """Rank tasks for a day in the given order. They move to that day; others lose their rank."""
    tasks = [session.get(Task, i) for i in task_ids]
    if None in tasks:
        raise LookupError("task not found")
    for task in session.scalars(
        select(Task).where(Task.planned_date == day, Task.top_rank.is_not(None))
    ):
        task.top_rank = None
    for task in tasks:
        task.top_rank = None
    session.flush()
    for rank, task in enumerate(tasks, start=1):
        task.planned_date, task.top_rank = day, rank
        task.version += 1
    events.record(session, "day.top_set", "day", None, day=day.isoformat(), task_ids=task_ids)
    return tasks


def focus(tasks: list[Task]) -> Task | None:
    """The first ranked task not yet done."""
    ranked = sorted((t for t in tasks if t.top_rank and not t.done_at), key=lambda t: t.top_rank)
    return ranked[0] if ranked else None


def top_three(session: Session, day: date) -> list[Task]:
    """The ranked tasks of a day, in order, dropped ones left out."""
    return list(
        session.scalars(
            select(Task)
            .where(Task.planned_date == day, Task.top_rank.is_not(None), Task.dropped_at.is_(None))
            .order_by(Task.top_rank)
        )
    )


def top_lines(tasks: list[Task]) -> list[str]:
    """Numbered lines for the top three, marking the ones done."""
    return [
        f"{t.top_rank}. {t.title} · {t.estimate_min} min" + (" (done)" if t.done_at else "")
        for t in tasks
    ]
