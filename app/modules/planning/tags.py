"""The goal tag shown on a task or item: the quarter goal it sits under."""

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.modules.planning import trace
from app.modules.planning.models import Goal


class Tag(BaseModel):
    id: int
    title: str
    short: str | None
    color: int | None


def tag_for(session: Session, goal_id: int | None) -> Tag | None:
    """The quarter goal above goal_id, or the theme itself for a goal linked to a theme."""
    steps = trace.chain(session, goal_id)
    if not steps:
        return None
    g = steps[1] if len(steps) > 1 else steps[0]
    return Tag(id=g.id, title=g.title, short=g.short, color=g.color)


def check_goal(session: Session, goal_id: int | None) -> None:
    """Answer 422 for a link to a goal that does not exist."""
    if goal_id is not None and session.get(Goal, goal_id) is None:
        raise HTTPException(422, "goal not found")
