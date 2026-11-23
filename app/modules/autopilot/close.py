"""Close learning blocks that have ended.

A block whose item was never started is missed: the item goes back to the inbox, top of
today's list, and the block counts as not kept. A started block becomes kept when it ends.
If its item is still in Learning, the time is saved as progress and the item is booked into
the next free block.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, events
from app.modules.autopilot import booking
from app.modules.day import blocks
from app.modules.day.models import TimeBlock
from app.modules.learning import lifecycle
from app.modules.learning.models import LearningItem


def ended(session: Session, *statuses: str) -> list[TimeBlock]:
    return list(
        session.scalars(
            select(TimeBlock)
            .where(
                TimeBlock.kind == "learning",
                TimeBlock.end <= clock.now(),
                TimeBlock.status.in_(statuses),
                TimeBlock.sync != "delete",
            )
            .order_by(TimeBlock.end)
        )
    )


def minutes_spent(item: LearningItem, block: TimeBlock) -> int:
    start = max(item.started_at or block.start, block.start)
    return max(int((block.end - start).total_seconds() // 60), 0)


def close_missed(session: Session, block: TimeBlock) -> None:
    item = session.get(LearningItem, block.item_id) if block.item_id else None
    blocks.change(session, block, status="missed")
    events.record(session, "block.missed", "time_block", block.id, item_id=block.item_id)
    if item and item.state == "booked":
        lifecycle.transition(session, item, "unbook")


def carry_on(session: Session, block: TimeBlock) -> None:
    """An item still in Learning after its block: save the time and book the next block."""
    item = session.get(LearningItem, block.item_id) if block.item_id else None
    if item is None or item.state != "learning" or booking.held_block(session, item):
        return
    item.progress_min += minutes_spent(item, block)
    booking.move(session, item, "return")


def run(session: Session) -> None:
    """Close every ended block once: planned ones were missed, started ones were kept."""
    for block in ended(session, "planned"):
        close_missed(session, block)
    for block in ended(session, "started"):
        carry_on(session, block)
        blocks.change(session, block, status="kept")
