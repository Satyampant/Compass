"""HTTP API for tasks."""

from datetime import date, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.kernel import clock, events, settings
from app.kernel.db import SessionDep
from app.modules.day.models import Task
from app.modules.day.service import create_task

router = APIRouter(prefix="/v1/tasks", tags=["day"])


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    estimate_min: int
    planned_date: date
    done_at: datetime | None
    version: int


class TaskIn(BaseModel):
    title: str
    estimate_min: int = 30
    planned_date: date | None = None


class TaskPatch(BaseModel):
    title: str | None = None
    estimate_min: int | None = None
    planned_date: date | None = None
    done: bool | None = None
    version: int | None = None


@router.post("", status_code=201)
def add_task(body: TaskIn, session: SessionDep) -> TaskOut:
    task = create_task(
        session, body.title, body.planned_date or settings.today(session), body.estimate_min
    )
    session.commit()
    return TaskOut.model_validate(task)


@router.patch("/{task_id}")
def edit_task(task_id: int, body: TaskPatch, session: SessionDep) -> TaskOut:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "task not found")
    if body.version is not None and body.version != task.version:
        raise HTTPException(409, "task changed elsewhere, reload")
    for field in ("title", "estimate_min", "planned_date"):
        if getattr(body, field) is not None:
            setattr(task, field, getattr(body, field))
    if body.done is not None and body.done != (task.done_at is not None):
        task.done_at = clock.now() if body.done else None
        events.record(session, "task.done" if body.done else "task.undone", "task", task.id)
    task.version += 1
    session.commit()
    return TaskOut.model_validate(task)
