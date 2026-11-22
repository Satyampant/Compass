"""GET /v1/today: everything the Today screen needs in one response."""

from datetime import date, datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.kernel import clock, settings
from app.kernel.db import SessionDep
from app.modules.autopilot import resurface
from app.modules.day.models import Task
from app.modules.day.router import TaskOut
from app.modules.learning import slots
from app.modules.learning.models import LearningItem
from app.modules.learning.router import ItemOut, item_out

router = APIRouter(prefix="/v1", tags=["day"])


class TodayOut(BaseModel):
    date: date
    tasks: list[TaskOut]
    revisit: list[ItemOut]
    inbox_count: int
    has_items: bool
    next_slot: datetime


@router.get("/today")
def today(session: SessionDep) -> TodayOut:
    day = settings.today(session)
    tasks = session.scalars(
        select(Task)
        .where(or_(Task.planned_date == day, (Task.planned_date < day) & Task.done_at.is_(None)))
        .order_by(Task.planned_date, Task.created_at)
    )
    count = lambda *where: session.scalar(  # noqa: E731
        select(func.count()).select_from(LearningItem).where(*where)
    )
    return TodayOut(
        date=day,
        tasks=[TaskOut.model_validate(t) for t in tasks],
        revisit=[item_out(i) for i in resurface.revisit_list(session)],
        inbox_count=count(LearningItem.state == "inbox"),
        has_items=count() > 0,
        next_slot=slots.next_slot(session, clock.now()),
    )
