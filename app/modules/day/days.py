"""HTTP API for a day as a whole: its top three."""

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.kernel.db import SessionDep
from app.modules.day import service
from app.modules.day.router import TaskOut, task_out

router = APIRouter(prefix="/v1/days", tags=["day"])


class TopIn(BaseModel):
    task_ids: list[int]


@router.put("/{day}/top-three")
def set_top_three(day: date, body: TopIn, session: SessionDep) -> list[TaskOut]:
    if len(set(body.task_ids)) != len(body.task_ids):
        raise HTTPException(422, "a task can hold one rank")
    try:
        tasks = service.set_top(session, day, body.task_ids)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    session.commit()
    return [task_out(session, t) for t in tasks]
