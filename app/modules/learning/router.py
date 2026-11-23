"""HTTP API for the learning queue."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, events
from app.kernel.db import SessionDep
from app.modules.autopilot import booking
from app.modules.learning import lifecycle
from app.modules.learning.models import LearningItem
from app.modules.planning.tags import Tag, check_goal, tag_for

router = APIRouter(prefix="/v1/learning-items", tags=["learning"])


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str | None
    source_type: str
    estimate_min: int
    progress_min: int
    state: str
    captured_at: datetime
    booked_for: datetime | None
    started_at: datetime | None
    closed_at: datetime | None
    note: str | None
    goal_id: int | None
    reason: str | None
    tag: Tag | None
    version: int
    actions: list[str]


class ItemPatch(BaseModel):
    title: str | None = None
    estimate_min: int | None = None
    goal_id: int | None = None
    reason: str | None = None
    version: int | None = None


class TransitionIn(BaseModel):
    action: str
    booked_for: datetime | None = None
    note: str | None = None


def item_out(session: Session, item: LearningItem) -> ItemOut:
    """Serialise an item with its goal tag and the moves valid for its state."""
    skip = {"actions", "tag"}
    fields = {name: getattr(item, name) for name in ItemOut.model_fields if name not in skip}
    return ItemOut(
        **fields,
        tag=tag_for(session, item.goal_id),
        actions=lifecycle.allowed_actions(item.state),
    )


def get_item(session: Session, item_id: int) -> LearningItem:
    """Load an item or answer 404."""
    item = session.get(LearningItem, item_id)
    if item is None:
        raise HTTPException(404, "item not found")
    return item


def check_version(current: int, sent: int | None) -> None:
    """Refuse an update made from a stale copy."""
    if sent is not None and sent != current:
        raise HTTPException(409, "item changed elsewhere, reload")


def link_goal(session: Session, item: LearningItem, goal_id: int | None) -> None:
    """Link or unlink a goal. An unlinked inbox item picks its schedule back up at once."""
    check_goal(session, goal_id)
    if goal_id == item.goal_id:
        return
    item.goal_id = goal_id
    if goal_id is None and item.state == "inbox" and item.next_resurface_at is None:
        item.next_resurface_at = clock.now()
    events.record(session, "item.goal_linked", "learning_item", item.id, goal_id=goal_id)


@router.get("")
def list_items(session: SessionDep, state: str | None = None) -> list[ItemOut]:
    query = select(LearningItem).order_by(LearningItem.captured_at.desc())
    if state:
        query = query.where(LearningItem.state.in_(state.split(",")))
    return [item_out(session, i) for i in session.scalars(query)]


@router.patch("/{item_id}")
def edit_item(item_id: int, body: ItemPatch, session: SessionDep) -> ItemOut:
    item = get_item(session, item_id)
    check_version(item.version, body.version)
    for field in ("title", "estimate_min"):
        if getattr(body, field) is not None:
            setattr(item, field, getattr(body, field))
    if "reason" in body.model_fields_set:
        item.reason = body.reason
    if "goal_id" in body.model_fields_set:
        link_goal(session, item, body.goal_id)
    item.version += 1
    session.commit()
    return item_out(session, item)


@router.post("/{item_id}/transitions")
def make_transition(item_id: int, body: TransitionIn, session: SessionDep) -> ItemOut:
    item = get_item(session, item_id)
    try:
        booking.move(session, item, body.action, booked_for=body.booked_for, note=body.note)
    except lifecycle.TransitionError as exc:
        raise HTTPException(409, str(exc)) from exc
    session.commit()
    return item_out(session, item)


class ProgressIn(BaseModel):
    minutes: int


@router.post("/{item_id}/progress")
def save_progress(item_id: int, body: ProgressIn, session: SessionDep) -> ItemOut:
    """Add minutes spent on an item, so the next block picks up where you stopped."""
    item = get_item(session, item_id)
    if item.state != "learning":
        raise HTTPException(409, "only an item in Learning has progress to save")
    item.progress_min = max(item.progress_min + body.minutes, 0)
    item.version += 1
    session.commit()
    return item_out(session, item)
