"""The goal tree: horizons, parents and limits."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.kernel import clock, events
from app.modules.planning.models import HORIZONS, Goal, KeyResult
from app.modules.planning.periods import period

LIMITS = {"year": 3, "quarter": 5, "week": 3}
MAX_KEY_RESULTS = 3
PARENT = {"quarter": "year", "month": "quarter", "week": "month"}
LIMIT_NAMES = {"year": "themes a year", "quarter": "goals a quarter", "week": "outcomes a week"}


class GoalError(ValueError):
    """A goal that breaks the tree's rules."""


@dataclass
class KeyResultIn:
    title: str
    target: float
    current: float = 0
    unit: str = ""


def create_goal(
    session: Session,
    horizon: str,
    title: str,
    day: date,
    *,
    parent_id: int | None = None,
    key_results: list[KeyResultIn] = (),
    due_date: date | None = None,
    short: str | None = None,
    color: int | None = None,
) -> Goal:
    """Add a goal for the period containing day, checking parent and limits."""
    if horizon not in HORIZONS:
        raise GoalError(f"unknown horizon {horizon}")
    check_parent(session, horizon, parent_id)
    start, end = period(horizon, day)
    check_limit(session, horizon, start)
    if horizon == "quarter" and not 1 <= len(key_results) <= MAX_KEY_RESULTS:
        raise GoalError("a quarter goal needs one to three key results")
    if horizon != "quarter" and key_results:
        raise GoalError("only quarter goals have key results")
    goal = Goal(
        horizon=horizon,
        title=title,
        parent_id=parent_id,
        period_start=start,
        period_end=end,
        due_date=due_date,
        short=short,
        color=color,
        created_at=clock.now(),
    )
    session.add(goal)
    session.flush()
    for kr in key_results:
        session.add(KeyResult(goal_id=goal.id, **kr.__dict__))
    events.record(session, "goal.created", "goal", goal.id, horizon=horizon)
    return goal


def check_parent(session: Session, horizon: str, parent_id: int | None) -> None:
    """A year theme has no parent. Every other goal has one, one horizon up."""
    if horizon == "year":
        if parent_id is not None:
            raise GoalError("a year theme has no parent")
        return
    parent = session.get(Goal, parent_id) if parent_id is not None else None
    if parent is None or parent.horizon != PARENT[horizon]:
        raise GoalError(f"a {horizon} goal needs a {PARENT[horizon]} parent")


def check_limit(session: Session, horizon: str, start: date) -> None:
    """Refuse a goal beyond the horizon's limit for its period."""
    if horizon not in LIMITS:
        return
    count = session.scalar(
        select(func.count())
        .select_from(Goal)
        .where(Goal.horizon == horizon, Goal.period_start == start)
    )
    if count >= LIMITS[horizon]:
        raise GoalError(f"at most {LIMITS[horizon]} {LIMIT_NAMES[horizon]}")


def add_key_result(session: Session, goal: Goal, kr: KeyResultIn) -> KeyResult:
    """Add a key result to a quarter goal that has fewer than three."""
    if goal.horizon != "quarter":
        raise GoalError("only quarter goals have key results")
    count = session.scalar(
        select(func.count()).select_from(KeyResult).where(KeyResult.goal_id == goal.id)
    )
    if count >= MAX_KEY_RESULTS:
        raise GoalError("a quarter goal has at most three key results")
    row = KeyResult(goal_id=goal.id, **kr.__dict__)
    session.add(row)
    session.flush()
    return row
