"""HTTP API for the learning queue."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock
from app.kernel.db import SessionDep
from app.modules.learning import lifecycle, slots
from app.modules.learning.models import LearningItem

router = APIRouter(prefix="/v1/learning-items", tags=["learning"])


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str | None
    source_type: str
    estimate_min: int
    state: str
    captured_at: datetime
    booked_for: datetime | None
    started_at: datetime | None
    closed_at: datetime | None
    note: str | None
    version: int
    actions: list[str]


class ItemPatch(BaseModel):
    title: str | None = None
    estimate_min: int | None = None
    version: int | None = None


class TransitionIn(BaseModel):
    action: str
    booked_for: datetime | None = None
    note: str | None = None


def item_out(item: LearningItem) -> ItemOut:
    """Serialise an item with the moves valid for its state."""
    fields = {name: getattr(item, name) for name in ItemOut.model_fields if name != "actions"}
    return ItemOut(**fields, actions=lifecycle.allowed_actions(item.state))


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


@router.get("")
def list_items(session: SessionDep, state: str | None = None) -> list[ItemOut]:
    query = select(LearningItem).order_by(LearningItem.captured_at.desc())
    if state:
        query = query.where(LearningItem.state.in_(state.split(",")))
    return [item_out(i) for i in session.scalars(query)]


@router.patch("/{item_id}")
def edit_item(item_id: int, body: ItemPatch, session: SessionDep) -> ItemOut:
    item = get_item(session, item_id)
    check_version(item.version, body.version)
    for field in ("title", "estimate_min"):
        if getattr(body, field) is not None:
            setattr(item, field, getattr(body, field))
    item.version += 1
    session.commit()
    return item_out(item)


@router.post("/{item_id}/transitions")
def make_transition(item_id: int, body: TransitionIn, session: SessionDep) -> ItemOut:
    item = get_item(session, item_id)
    booked_for = body.booked_for
    if body.action == "book" and booked_for is None:
        booked_for = slots.next_slot(session, clock.now())
    try:
        lifecycle.transition(session, item, body.action, booked_for=booked_for, note=body.note)
    except lifecycle.TransitionError as exc:
        raise HTTPException(409, str(exc)) from exc
    session.commit()
    return item_out(item)
