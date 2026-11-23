"""HTTP API for a day as a whole: its top three and its plan."""

from datetime import date, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.kernel import clock, events
from app.kernel.db import SessionDep
from app.modules.day import blocks_api, plan, service
from app.modules.day.blocks_api import BlockOut, block_out
from app.modules.day.models import DailyLog, Task
from app.modules.day.router import TaskOut, task_out

router = APIRouter(prefix="/v1/days", tags=["day"])


class TopIn(BaseModel):
    task_ids: list[int]


class DecisionIn(BaseModel):
    task_id: int
    action: str
    to: date | None = None


class PlacementIO(BaseModel):
    task_id: int
    start: datetime
    end: datetime


class PlanIn(BaseModel):
    decisions: list[DecisionIn] = []
    top: list[int] = []
    blocks: list[PlacementIO] | None = None


class ProposeIn(BaseModel):
    task_ids: list[int]


class PlanDraft(BaseModel):
    date: date
    open: list[TaskOut]
    planned: list[TaskOut]
    blocks: list[BlockOut]


class PlanOut(BaseModel):
    date: date
    planned_at: str
    top: list[TaskOut]


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


@router.get("/{day}/plan")
def plan_draft(day: date, session: SessionDep) -> PlanDraft:
    return PlanDraft(
        date=day,
        open=[task_out(session, t) for t in plan.open_tasks(session, day)],
        planned=[task_out(session, t) for t in plan.planned(session, day)],
        blocks=[block_out(session, b) for b in blocks_api.day_blocks(session, day)],
    )


@router.post("/{day}/propose")
def propose(day: date, body: ProposeIn, session: SessionDep) -> list[PlacementIO]:
    """Blocks for the given tasks around the day's meetings, for you to adjust."""
    missing = [i for i in body.task_ids if session.get(Task, i) is None]
    if missing:
        raise HTTPException(404, f"task {missing[0]} not found")
    return [PlacementIO(**p.__dict__) for p in plan.propose(session, day, body.task_ids)]


@router.post("/{day}/plan")
def commit_plan(day: date, body: PlanIn, session: SessionDep) -> PlanOut:
    if len(set(body.top)) != len(body.top):
        raise HTTPException(422, "a task can hold one rank")
    decisions = [plan.Decision(**d.model_dump()) for d in body.decisions]
    try:
        placements = (
            None if body.blocks is None else [plan.Placement(**b.model_dump()) for b in body.blocks]
        )
        log = plan.commit(session, day, decisions, body.top, placements)
    except (plan.PlanError, LookupError) as exc:
        raise HTTPException(422, str(exc)) from exc
    session.commit()
    top = [t for t in plan.planned(session, day) if t.top_rank]
    return PlanOut(
        date=day, planned_at=log.planned_at.isoformat(), top=[task_out(session, t) for t in top]
    )


class ShutdownIn(BaseModel):
    learned_line: str = Field(min_length=1, max_length=500)


class ShutdownOut(BaseModel):
    date: date
    closed_at: datetime
    learned_line: str


@router.post("/{day}/shutdown")
def shutdown(day: date, body: ShutdownIn, session: SessionDep) -> ShutdownOut:
    log = session.get(DailyLog, day) or DailyLog(day=day)
    log.closed_at = clock.now()
    log.learned_line = body.learned_line.strip()
    session.add(log)
    events.record(session, "day.closed", "day", None, day=day.isoformat())
    session.commit()
    return ShutdownOut(date=day, closed_at=log.closed_at, learned_line=log.learned_line)
