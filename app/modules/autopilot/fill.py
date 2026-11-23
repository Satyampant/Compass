"""Fill each empty protected slot with the best item that fits.

Score, as in the architecture: started items first, then items you booked whose slot was lost,
then goal-linked items, then older ones, and finally how well the item fits the slot.
Items pinned to today's list wait for your decision and are not booked for you.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock
from app.modules.day import blocks
from app.modules.day.models import TimeBlock
from app.modules.learning import lifecycle
from app.modules.learning.models import LearningItem

FIT_SLACK_MIN = 10
EMPTY_TITLE = "Learning block"


def remaining(item: LearningItem) -> int:
    return max(item.estimate_min - item.progress_min, 5)


def fit(item: LearningItem, slot_min: int) -> float:
    """1 when the item fills the slot exactly, less the more it leaves empty."""
    return max(0.0, 1 - abs(slot_min - remaining(item)) / slot_min)


def score(item: LearningItem, slot_min: int, now: datetime) -> float:
    age = (now - item.captured_at).days
    return (
        40 * (item.started_at is not None)
        + 35 * (item.state == "booked")
        + 30 * (item.goal_id is not None)
        + 20 * min(age, 21) / 21
        + 10 * fit(item, slot_min)
    )


def held_items(session: Session, now: datetime) -> set[int]:
    """Items that already hold an upcoming block."""
    return set(
        session.scalars(
            select(TimeBlock.item_id).where(
                TimeBlock.item_id.is_not(None),
                TimeBlock.end > now,
                TimeBlock.status == "planned",
            )
        )
    )


def candidates(session: Session, slot: TimeBlock, skip: set[int]) -> list[LearningItem]:
    """Open items without a block that fit the slot, best first."""
    now = clock.now()
    slot_min = int((slot.end - slot.start).total_seconds() // 60)
    held = held_items(session, now) | skip
    pool = [
        i
        for i in session.scalars(
            select(LearningItem).where(LearningItem.state.in_(("inbox", "booked", "learning")))
        )
        if i.id not in held
        and not (i.state == "inbox" and i.pinned_at)
        and (i.state == "learning" or remaining(i) <= slot_min + FIT_SLACK_MIN)
    ]
    return sorted(pool, key=lambda i: (-score(i, slot_min, now), i.captured_at))


def attach(session: Session, slot: TimeBlock, item: LearningItem) -> None:
    """Put an item in a slot, booking it if it came from the inbox."""
    if item.state == "inbox":
        lifecycle.transition(session, item, "book", booked_for=slot.start)
    elif item.state == "booked":
        item.booked_for = slot.start
    blocks.change(session, slot, item_id=item.id, title=f"Learning: {item.title}")


def detach(session: Session, slot: TimeBlock) -> None:
    """Empty a slot. A slot Compass made only for one booking goes away."""
    if slot.protected:
        blocks.change(session, slot, item_id=None, title=EMPTY_TITLE)
    else:
        blocks.remove(session, slot)


def empty_slots(session: Session) -> list[TimeBlock]:
    return list(
        session.scalars(
            select(TimeBlock)
            .where(
                TimeBlock.protected.is_(True),
                TimeBlock.item_id.is_(None),
                TimeBlock.status == "planned",
                TimeBlock.start > clock.now(),
                TimeBlock.sync != "delete",
            )
            .order_by(TimeBlock.start)
        )
    )


def run(session: Session) -> int:
    """Fill every empty upcoming slot, earliest first. Returns how many were filled."""
    filled = 0
    for slot in empty_slots(session):
        best = candidates(session, slot, set())
        if best:
            attach(session, slot, best[0])
            session.flush()
            filled += 1
    return filled


def swap(session: Session, slot: TimeBlock) -> LearningItem | None:
    """One tap: put the next best item in the slot. The one taken out goes back to the inbox."""
    old = session.get(LearningItem, slot.item_id) if slot.item_id else None
    skip = {old.id} if old else set()
    if old and old.state == "booked":
        lifecycle.transition(session, old, "unbook")
    detach(session, slot)
    session.flush()
    best = candidates(session, slot, skip)
    if best:
        attach(session, slot, best[0])
        return best[0]
    return None
