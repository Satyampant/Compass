"""Tasks for a day."""

from datetime import date

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
