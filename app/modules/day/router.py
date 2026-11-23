"""HTTP API for tasks."""

from datetime import date, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.kernel import clock, events, settings
from app.kernel.db import SessionDep
from app.modules.day.models import Task
from app.modules.day.service import create_task
from app.modules.planning.tags import Tag, check_goal, tag_for

router = APIRouter(prefix="/v1/tasks", tags=["day"])


class TaskOut(BaseModel):
    id: int
    title: str
    estimate_min: int
    planned_date: date
    done_at: datetime | None
    goal_id: int | None
    tag: Tag | None
    top_rank: int | None
    version: int


class TaskIn(BaseModel):
    title: str
    estimate_min: int = 30
    planned_date: date | None = None
    goal_id: int | None = None


class TaskPatch(BaseModel):
    title: str | None = None
    estimate_min: int | None = None
    planned_date: date | None = None
    goal_id: int | None = None
    done: bool | None = None
    version: int | None = None


def task_out(session: Session, task: Task) -> TaskOut:
    """Serialise a task with the tag of the goal it serves. No tag means untied."""
    return TaskOut(
        id=task.id,
        title=task.title,
        estimate_min=task.estimate_min,
        planned_date=task.planned_date,
        done_at=task.done_at,
        goal_id=task.goal_id,
        tag=tag_for(session, task.goal_id),
        top_rank=task.top_rank,
        version=task.version,
    )


@router.post("", status_code=201)
def add_task(body: TaskIn, session: SessionDep) -> TaskOut:
    check_goal(session, body.goal_id)
    task = create_task(
        session,
        body.title,
        body.planned_date or settings.today(session),
        body.estimate_min,
        goal_id=body.goal_id,
    )
    session.commit()
    return task_out(session, task)


@router.patch("/{task_id}")
def edit_task(task_id: int, body: TaskPatch, session: SessionDep) -> TaskOut:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "task not found")
    if body.version is not None and body.version != task.version:
        raise HTTPException(409, "task changed elsewhere, reload")
    if body.planned_date is not None and body.planned_date != task.planned_date:
        task.planned_date, task.top_rank = body.planned_date, None
    for field in ("title", "estimate_min"):
        if getattr(body, field) is not None:
            setattr(task, field, getattr(body, field))
    if "goal_id" in body.model_fields_set:
        check_goal(session, body.goal_id)
        task.goal_id = body.goal_id
    if body.done is not None and body.done != (task.done_at is not None):
        task.done_at = clock.now() if body.done else None
        events.record(session, "task.done" if body.done else "task.undone", "task", task.id)
    task.version += 1
    session.commit()
    return task_out(session, task)
