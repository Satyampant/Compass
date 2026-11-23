"""Protected learning slots: four a week from settings, moved off meetings when they clash.

Each slot remembers its nominal start (slot_at). A meeting on it moves the slot to the next
free stretch of its length that day, inside the day window. With no room left the slot is
marked not kept and its item returns to the top of today's list.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, settings
from app.modules.day import blocks
from app.modules.day.blocks_api import window
from app.modules.day.models import TimeBlock
from app.modules.learning import lifecycle
from app.modules.learning.models import LearningItem

STEP = timedelta(minutes=15)


def nominal_slots(session: Session, week_start: date) -> list[datetime]:
    """The week's slot starts from settings."""
    tz = settings.tz(session)
    return sorted(
        datetime.combine(
            week_start + timedelta(days=s["weekday"]), time.fromisoformat(s["time"]), tz
        )
        for s in settings.get(session, "learning_slots")
    )


def ensure_week(session: Session, week_start: date) -> list[TimeBlock]:
    """Create the week's missing slots that still lie ahead."""
    length = timedelta(minutes=settings.get(session, "learning_block_min"))
    now, made = clock.now(), []
    for at in nominal_slots(session, week_start):
        exists = session.scalar(select(TimeBlock.id).where(TimeBlock.slot_at == at))
        if exists or at <= now:
            continue
        slot = blocks.create(
            session, "learning", at, at + length, "Learning block", protected=True, slot_at=at
        )
        made.append(slot)
    return made


def busy(session: Session, start: datetime, end: datetime, skip: int) -> bool:
    """True when anything else, meeting or block, overlaps the span."""
    return (
        session.scalar(
            select(TimeBlock.id).where(
                TimeBlock.id != skip,
                TimeBlock.start < end,
                TimeBlock.end > start,
                TimeBlock.sync != "delete",
                TimeBlock.status != "not_kept",
            )
        )
        is not None
    )


def place(session: Session, slot: TimeBlock) -> datetime | None:
    """The first free start from the slot's nominal time on, or None if the day is full."""
    length = slot.end - slot.start
    tz = settings.tz(session)
    _, last = window(session, slot.slot_at.astimezone(tz).date())
    at = slot.slot_at
    while at + length <= last:
        if not busy(session, at, at + length, slot.id):
            return at
        at += STEP
    return None


def resolve(session: Session, slot: TimeBlock) -> None:
    """Keep the slot where it is if free, otherwise move it or mark it not kept."""
    at = place(session, slot)
    if at is None:
        if slot.status != "not_kept":
            item = session.get(LearningItem, slot.item_id) if slot.item_id else None
            blocks.change(session, slot, status="not_kept", item_id=None)
            if item and item.state == "booked":
                lifecycle.transition(session, item, "unbook")
        return
    if at != slot.start or slot.status == "not_kept":
        length = slot.end - slot.start
        blocks.change(session, slot, start=at, end=at + length, status="planned")
        item = session.get(LearningItem, slot.item_id) if slot.item_id else None
        if item and item.state == "booked":
            item.booked_for = at


def run(session: Session) -> None:
    """Ensure this week's and next week's slots, then move any that clash."""
    today = settings.today(session)
    monday = today - timedelta(days=today.weekday())
    for week in (monday, monday + timedelta(days=7)):
        ensure_week(session, week)
    session.flush()
    upcoming = session.scalars(
        select(TimeBlock)
        .where(
            TimeBlock.protected.is_(True),
            TimeBlock.start > clock.now(),
            TimeBlock.status.in_(("planned", "not_kept")),
        )
        .order_by(TimeBlock.slot_at)
    )
    for slot in upcoming:
        resolve(session, slot)
