"""HTTP API for time blocks."""

from datetime import date, datetime, time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import settings
from app.kernel.db import SessionDep
from app.modules.day.models import Task, TimeBlock
from app.modules.learning.models import LearningItem
from app.modules.planning.tags import Tag, tag_for

router = APIRouter(prefix="/v1/blocks", tags=["day"])


class BlockOut(BaseModel):
    id: int
    kind: str
    source: str
    title: str
    start: datetime
    end: datetime
    task_id: int | None
    item_id: int | None
    item_url: str | None
    protected: bool
    status: str
    tag: Tag | None
    version: int


class Mark(BaseModel):
    at: datetime
    label: str


def block_out(session: Session, block: TimeBlock) -> BlockOut:
    """Serialise a block with the goal tag of what it holds."""
    goal_id, url = None, None
    if block.task_id:
        goal_id = session.get(Task, block.task_id).goal_id
    if block.item_id:
        item = session.get(LearningItem, block.item_id)
        goal_id, url = item.goal_id, item.url
    return BlockOut(
        id=block.id,
        kind=block.kind,
        source=block.source,
        title=block.title,
        start=block.start,
        end=block.end,
        task_id=block.task_id,
        item_id=block.item_id,
        item_url=url,
        protected=block.protected,
        status=block.status,
        tag=tag_for(session, goal_id),
        version=block.version,
    )


def window(session: Session, day: date) -> tuple[datetime, datetime]:
    """The day window, 08:00 to 20:00 by default, as aware moments."""
    tz = settings.tz(session)
    first, last = settings.get(session, "day_window")
    return (
        datetime.combine(day, time.fromisoformat(first), tz),
        datetime.combine(day, time.fromisoformat(last), tz),
    )


def day_blocks(session: Session, day: date) -> list[TimeBlock]:
    """Blocks that overlap the day window, earliest first. Blocks being deleted are left out."""
    start, end = window(session, day)
    return list(
        session.scalars(
            select(TimeBlock)
            .where(TimeBlock.start < end, TimeBlock.end > start, TimeBlock.sync != "delete")
            .order_by(TimeBlock.start, TimeBlock.end)
        )
    )


def day_marks(session: Session, day: date) -> list[Mark]:
    """Fixed moments drawn across the list, such as NSE open and close on weekdays."""
    tz = settings.tz(session)
    return [
        Mark(at=datetime.combine(day, time.fromisoformat(m["time"]), tz), label=m["label"])
        for m in settings.get(session, "day_marks")
        if day.weekday() < 5 or not m.get("weekdays")
    ]


@router.post("/{block_id}/swap")
def swap(block_id: int, session: SessionDep) -> BlockOut:
    """Put the next best item in a protected slot."""
    from app.modules.autopilot import fill

    block = session.get(TimeBlock, block_id)
    if block is None:
        raise HTTPException(404, "block not found")
    if not block.protected or block.status != "planned":
        raise HTTPException(409, "only an upcoming learning slot can be swapped")
    fill.swap(session, block)
    session.commit()
    return block_out(session, block)
