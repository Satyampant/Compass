"""HTTP API for goals and key results."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.kernel import clock, events, settings
from app.kernel.db import SessionDep
from app.modules.day.models import Task
from app.modules.planning import prompts, service, trace
from app.modules.planning.models import Goal, KeyResult
from app.modules.planning.periods import period

router = APIRouter(prefix="/v1", tags=["planning"])
Horizon = Literal["year", "quarter", "month", "week"]


class KeyResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    target: float
    current: float
    unit: str
    version: int


class GoalOut(BaseModel):
    id: int
    horizon: str
    title: str
    parent_id: int | None
    period_start: date
    period_end: date
    due_date: date | None
    short: str | None
    color: int | None
    draft: bool
    done: bool
    progress: float
    pace: float | None
    pace_status: str | None
    key_results: list[KeyResultOut]
    version: int


class TraceStep(BaseModel):
    id: int
    horizon: str
    title: str
    short: str | None
    color: int | None


class KeyResultIn(BaseModel):
    title: str = Field(min_length=1)
    target: float = Field(gt=0)
    current: float = 0
    unit: str = ""


class GoalIn(BaseModel):
    horizon: str
    title: str = Field(min_length=1)
    parent_id: int | None = None
    on: date | None = None
    due_date: date | None = None
    short: str | None = None
    color: int | None = None
    key_results: list[KeyResultIn] = []


class GoalPatch(BaseModel):
    title: str | None = None
    parent_id: int | None = None
    due_date: date | None = None
    short: str | None = None
    color: int | None = None
    done: bool | None = None
    version: int | None = None


class KeyResultPatch(BaseModel):
    title: str | None = None
    target: float | None = Field(default=None, gt=0)
    current: float | None = None
    version: int | None = None


def goal_out(session: Session, goal: Goal) -> GoalOut:
    """Serialise a goal with its progress and key results."""
    progress = trace.progress(session, goal)
    pace, status = None, None
    if goal.horizon == "quarter":
        pace = trace.pace(goal.period_start, goal.period_end, settings.today(session))
        status = trace.pace_status(
            progress,
            pace,
            settings.get(session, "pace_on_track_points"),
            settings.get(session, "pace_at_risk_points"),
        )
    krs = session.scalars(
        select(KeyResult).where(KeyResult.goal_id == goal.id).order_by(KeyResult.id)
    )
    return GoalOut(
        id=goal.id,
        horizon=goal.horizon,
        title=goal.title,
        parent_id=goal.parent_id,
        period_start=goal.period_start,
        period_end=goal.period_end,
        due_date=goal.due_date,
        short=goal.short,
        color=goal.color,
        draft=goal.draft,
        done=goal.done_at is not None,
        progress=progress,
        pace=pace,
        pace_status=status,
        key_results=[KeyResultOut.model_validate(kr) for kr in krs],
        version=goal.version,
    )


def trace_out(goals: list[Goal]) -> list[TraceStep]:
    """A chain as the steps the trace line shows."""
    return [
        TraceStep(id=g.id, horizon=g.horizon, title=g.title, short=g.short, color=g.color)
        for g in goals
    ]


def get_goal(session: Session, goal_id: int) -> Goal:
    """Load a goal or answer 404."""
    goal = session.get(Goal, goal_id)
    if goal is None:
        raise HTTPException(404, "goal not found")
    return goal


def check_version(current: int, sent: int | None) -> None:
    """Refuse an update made from a stale copy."""
    if sent is not None and sent != current:
        raise HTTPException(409, "changed elsewhere, reload")


@router.get("/goals")
def list_goals(session: SessionDep, horizon: Horizon, on: date | None = None) -> list[GoalOut]:
    start, _ = period(horizon, on or settings.today(session))
    goals = session.scalars(
        select(Goal).where(Goal.horizon == horizon, Goal.period_start == start).order_by(Goal.id)
    )
    return [goal_out(session, g) for g in goals]


@router.post("/goals", status_code=201)
def create_goal(body: GoalIn, session: SessionDep) -> GoalOut:
    try:
        goal = service.create_goal(
            session,
            body.horizon,
            body.title,
            body.on or settings.today(session),
            parent_id=body.parent_id,
            key_results=[service.KeyResultIn(**kr.model_dump()) for kr in body.key_results],
            due_date=body.due_date,
            short=body.short,
            color=body.color,
        )
    except service.GoalError as exc:
        raise HTTPException(422, str(exc)) from exc
    session.commit()
    return goal_out(session, goal)


@router.patch("/goals/{goal_id}")
def edit_goal(goal_id: int, body: GoalPatch, session: SessionDep) -> GoalOut:
    goal = get_goal(session, goal_id)
    check_version(goal.version, body.version)
    if body.parent_id is not None and body.parent_id != goal.parent_id:
        if not goal.draft:
            raise HTTPException(409, "only a draft can take a new parent")
        try:
            service.confirm_draft(session, goal, body.parent_id)
        except service.GoalError as exc:
            raise HTTPException(422, str(exc)) from exc
    for field in ("title", "due_date", "short", "color"):
        if field in body.model_fields_set:
            setattr(goal, field, getattr(body, field))
    if body.done is not None and body.done != (goal.done_at is not None):
        goal.done_at = clock.now() if body.done else None
        events.record(session, "goal.done" if body.done else "goal.undone", "goal", goal.id)
    goal.version += 1
    session.commit()
    return goal_out(session, goal)


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: int, session: SessionDep) -> None:
    goal = get_goal(session, goal_id)
    if session.scalar(select(Goal.id).where(Goal.parent_id == goal.id).limit(1)):
        raise HTTPException(409, "remove the goals under it first")
    session.execute(update(Task).where(Task.goal_id == goal.id).values(goal_id=None))
    for kr in session.scalars(select(KeyResult).where(KeyResult.goal_id == goal.id)):
        session.delete(kr)
    session.delete(goal)
    events.record(session, "goal.deleted", "goal", goal_id)
    session.commit()


@router.get("/goals/{goal_id}/trace")
def goal_trace(goal_id: int, session: SessionDep) -> list[TraceStep]:
    get_goal(session, goal_id)
    return trace_out(trace.chain(session, goal_id))


@router.post("/goals/{goal_id}/key-results", status_code=201)
def add_key_result(goal_id: int, body: KeyResultIn, session: SessionDep) -> KeyResultOut:
    goal = get_goal(session, goal_id)
    try:
        kr = service.add_key_result(session, goal, service.KeyResultIn(**body.model_dump()))
    except service.GoalError as exc:
        raise HTTPException(422, str(exc)) from exc
    session.commit()
    return KeyResultOut.model_validate(kr)


@router.patch("/key-results/{kr_id}")
def edit_key_result(kr_id: int, body: KeyResultPatch, session: SessionDep) -> KeyResultOut:
    kr = session.get(KeyResult, kr_id)
    if kr is None:
        raise HTTPException(404, "key result not found")
    check_version(kr.version, body.version)
    for field in ("title", "target", "current"):
        if getattr(body, field) is not None:
            setattr(kr, field, getattr(body, field))
    kr.version += 1
    session.commit()
    return KeyResultOut.model_validate(kr)


class Prompt(BaseModel):
    horizon: Horizon
    starts: date
    label: str


@router.get("/planning/prompts")
def planning_prompts(session: SessionDep) -> list[Prompt]:
    """Planning that is open now: next quarter from the 24th of its last month, next year
    from 1 December."""
    return [Prompt(**p) for p in prompts.open_prompts(session, settings.today(session))]
