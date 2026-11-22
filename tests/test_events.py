from datetime import date

from sqlalchemy import func, select

from app.kernel import clock, events
from app.kernel.models import Event
from app.modules.day.models import Task


def test_event_commits_with_change(session):
    task = Task(title="a", planned_date=date(2026, 11, 23), created_at=clock.now())
    session.add(task)
    session.flush()
    events.record(session, "task.created", "task", task.id, title="a")
    session.commit()
    assert session.scalars(select(Event)).one().data == {"title": "a"}


def test_rolled_back_change_leaves_no_event(session):
    task = Task(title="a", planned_date=date(2026, 11, 23), created_at=clock.now())
    session.add(task)
    session.flush()
    events.record(session, "task.created", "task", task.id)
    session.rollback()
    assert session.scalar(select(func.count()).select_from(Event)) == 0
    assert session.scalar(select(func.count()).select_from(Task)) == 0
