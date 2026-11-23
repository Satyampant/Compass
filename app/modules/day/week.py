"""GET /v1/week: the week board, with planned hours per day against capacity."""

from datetime import date, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.kernel import clock, settings
from app.kernel.db import SessionDep
from app.modules.day.models import Task
from app.modules.day.router import TaskOut, task_out

router = APIRouter(prefix="/v1", tags=["day"])


class DayColumn(BaseModel):
    date: date
    tasks: list[TaskOut]
    planned_min: int
    capacity_min: int
    over: bool


class WeekOut(BaseModel):
    start: date
    days: list[DayColumn]
    planned_min: int
    capacity_min: int
    over: bool


def capacity_min(session, day: date) -> int:
    """Hours available on a day: weekdays and weekends differ."""
    key = "capacity_weekend_hours" if day.weekday() >= 5 else "capacity_weekday_hours"
    return int(settings.get(session, key) * 60)


@router.get("/week")
def week(session: SessionDep, on: date | None = None) -> WeekOut:
    start = clock.week_start(on or settings.today(session))
    end = start + timedelta(days=6)
    tasks = session.scalars(
        select(Task)
        .where(Task.planned_date.between(start, end))
        .order_by(Task.top_rank.is_(None), Task.top_rank, Task.created_at)
    ).all()
    days = []
    for n in range(7):
        day = start + timedelta(days=n)
        mine = [t for t in tasks if t.planned_date == day]
        planned = sum(t.estimate_min for t in mine)
        cap = capacity_min(session, day)
        days.append(
            DayColumn(
                date=day,
                tasks=[task_out(session, t) for t in mine],
                planned_min=planned,
                capacity_min=cap,
                over=planned > cap,
            )
        )
    total = sum(d.planned_min for d in days)
    week_cap = int(settings.get(session, "capacity_week_hours") * 60)
    return WeekOut(
        start=start, days=days, planned_min=total, capacity_min=week_cap, over=total > week_cap
    )
