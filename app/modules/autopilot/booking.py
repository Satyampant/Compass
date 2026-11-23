"""Item moves that reserve or release a learning block. The web app and the bot call these.

Booking takes the next empty protected slot, or a new block at the time you picked.
Unbooking or letting go frees the block. Returning an item from Learning books it again.
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.kernel import clock, settings
from app.modules.autopilot import fill
from app.modules.day import blocks
from app.modules.day.models import TimeBlock
from app.modules.learning import lifecycle, slots
from app.modules.learning.models import LearningItem


def held_block(session: Session, item: LearningItem) -> TimeBlock | None:
    """The upcoming block an item holds, if any."""
    return session.scalars(
        select(TimeBlock).where(TimeBlock.item_id == item.id, TimeBlock.status == "planned")
    ).first()


def reserve(session: Session, item: LearningItem, at: datetime | None) -> TimeBlock:
    """The slot an item will take: an empty protected slot at `at` (or the earliest one), or a
    new block at `at`. With every slot taken, a new slot after the last one held."""
    empty = fill.empty_slots(session)
    match = [s for s in empty if at is None or s.start == at]
    if match:
        return match[0]
    length = timedelta(minutes=settings.get(session, "learning_block_min"))
    if at is not None:
        return blocks.create(session, "learning", at, at + length, fill.EMPTY_TITLE)
    last = session.scalar(select(func.max(TimeBlock.slot_at)).where(TimeBlock.protected.is_(True)))
    at = slots.next_slot(session, max(last or clock.now(), clock.now()))
    return blocks.create(
        session, "learning", at, at + length, fill.EMPTY_TITLE, protected=True, slot_at=at
    )


def release(session: Session, item: LearningItem) -> None:
    block = held_block(session, item)
    if block:
        fill.detach(session, block)


def move(
    session: Session,
    item: LearningItem,
    action: str,
    *,
    booked_for: datetime | None = None,
    note: str | None = None,
) -> LearningItem:
    """Apply a person's move, with the block it reserves or frees."""
    if action in ("book", "return"):
        lifecycle.check(item, action)
        if action == "return":
            release(session, item)
        slot = reserve(session, item, booked_for)
        lifecycle.transition(session, item, action, booked_for=slot.start, note=note)
        blocks.change(session, slot, item_id=item.id, title=f"Learning: {item.title}")
        return item
    was_booked = item.state == "booked"
    lifecycle.transition(session, item, action, booked_for=booked_for, note=note)
    if was_booked and action in ("unbook", "let_go"):
        release(session, item)
    return item
