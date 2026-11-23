"""The chain from a goal or task up to its year theme, and progress rolled up from key results."""

from datetime import date

from sqlalchemy import literal, select
from sqlalchemy.orm import Session

from app.modules.day.models import Task
from app.modules.planning.models import Goal, KeyResult


def chain(session: Session, goal_id: int | None) -> list[Goal]:
    """The goal and its ancestors in one query, year theme first."""
    if goal_id is None:
        return []
    up = select(Goal.id, Goal.parent_id, literal(0).label("depth")).where(Goal.id == goal_id)
    up = up.cte("up", recursive=True)
    up = up.union_all(
        select(Goal.id, Goal.parent_id, (up.c.depth + 1).label("depth")).join(
            up, Goal.id == up.c.parent_id
        )
    )
    rows = session.scalars(select(Goal).join(up, Goal.id == up.c.id).order_by(up.c.depth.desc()))
    return list(rows)


def task_chain(session: Session, task_id: int) -> list[Goal]:
    """The chain above a task, empty when the task is untied."""
    return chain(session, session.scalar(select(Task.goal_id).where(Task.id == task_id)))


def kr_progress(kr: KeyResult) -> float:
    """Share of the target reached, capped at one."""
    return min(kr.current / kr.target, 1.0) if kr.target else 0.0


def progress(session: Session, goal: Goal) -> float:
    """Progress from 0 to 1.

    Quarter goals average their key results, year themes average their quarter goals,
    and milestones and outcomes are done or not.
    """
    if goal.horizon == "quarter":
        krs = session.scalars(select(KeyResult).where(KeyResult.goal_id == goal.id)).all()
        return _mean([kr_progress(kr) for kr in krs])
    if goal.horizon == "year":
        children = session.scalars(select(Goal).where(Goal.parent_id == goal.id)).all()
        return _mean([progress(session, child) for child in children])
    return 1.0 if goal.done_at else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def pace(start: date, end: date, today: date) -> float:
    """Share of the period gone, counting today: day 54 of 92 is 54 / 92."""
    total = (end - start).days + 1
    gone = min(max((today - start).days + 1, 0), total)
    return gone / total


def pace_status(progress: float, pace_share: float, on_track: int, at_risk: int) -> str:
    """On track within `on_track` points of pace, at risk within `at_risk`, behind beyond."""
    gap = (pace_share - progress) * 100
    return "on_track" if gap <= on_track else "at_risk" if gap <= at_risk else "behind"
