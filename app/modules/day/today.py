"""GET /v1/today: everything the Today screen needs in one response."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.kernel import clock, settings
from app.kernel.db import SessionDep
from app.modules.autopilot import resurface
from app.modules.day import service
from app.modules.day.models import DailyLog, Task
from app.modules.day.router import TaskOut, task_out
from app.modules.learning import slots
from app.modules.learning.models import LearningItem
from app.modules.learning.router import ItemOut, item_out
from app.modules.planning import trace
from app.modules.planning.router import TraceStep, trace_out

router = APIRouter(prefix="/v1", tags=["day"])


class Focus(BaseModel):
    task: TaskOut
    trace: list[TraceStep]


class TodayOut(BaseModel):
    date: date
    focus: Focus | None
    top_limit: int
    closed_at: datetime | None
    learned_line: str | None
    tomorrow_planned: bool
    tasks: list[TaskOut]
    revisit: list[ItemOut]
    inbox_count: int
    has_items: bool
    next_slot: datetime


@router.get("/today")
def today(session: SessionDep) -> TodayOut:
    day = settings.today(session)
    tasks = session.scalars(
        select(Task).where(
            or_(Task.planned_date == day, (Task.planned_date < day) & Task.done_at.is_(None)),
            Task.dropped_at.is_(None),
        )
    )
    ranked = lambda t: t.top_rank if t.planned_date == day and t.top_rank else None  # noqa: E731
    tasks = sorted(
        tasks, key=lambda t: (ranked(t) is None, ranked(t) or 0, t.planned_date, t.created_at)
    )
    top = service.focus([t for t in tasks if t.planned_date == day])
    log = session.get(DailyLog, day)
    nxt = session.get(DailyLog, day + timedelta(days=1))
    count = lambda *where: session.scalar(  # noqa: E731
        select(func.count()).select_from(LearningItem).where(*where)
    )
    return TodayOut(
        date=day,
        focus=top
        and Focus(task=task_out(session, top), trace=trace_out(trace.chain(session, top.goal_id))),
        top_limit=settings.get(session, "top_priorities"),
        closed_at=log.closed_at if log else None,
        learned_line=log.learned_line if log else None,
        tomorrow_planned=bool(nxt and nxt.planned_at),
        tasks=[task_out(session, t) for t in tasks],
        revisit=[item_out(session, i) for i in resurface.revisit_list(session)],
        inbox_count=count(LearningItem.state == "inbox"),
        has_items=count() > 0,
        next_slot=slots.next_slot(session, clock.now()),
    )
