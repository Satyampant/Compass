"""Nudges tied to the clock: a reminder before each learning block and the shutdown nudge.

Both are dropped when they come too late, so a long sleep ends in one brief, not a backlog.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.kernel import clock, jobs, settings
from app.modules.day.models import DailyLog, TimeBlock
from app.modules.learning.models import LearningItem
from app.modules.learning.telegram import short_time
from app.modules.notify.service import Nudge, send_nudges


def block_nudge(session: Session, block: TimeBlock, item: LearningItem) -> Nudge:
    lines = [f"Learning block at {short_time(session, block.start)}: {item.title}"]
    if item.url:
        lines.append(item.url)
    if item.progress_min:
        lines.append(f"Picks up at {item.progress_min} of {item.estimate_min} min")
    return Nudge("block_reminder", "\n".join(lines), item_id=item.id)


@jobs.handler("block_reminder")
def block_reminder(session: Session, payload: dict) -> None:
    """Job: remind before a block, unless it moved, lost its item or has already begun."""
    block = session.get(TimeBlock, payload["block_id"])
    if block is None or block.start.isoformat() != payload["start"]:
        return
    if block.status != "planned" or not block.item_id or clock.now() >= block.start:
        return
    send_nudges(session, [block_nudge(session, block, session.get(LearningItem, block.item_id))])


SHUTDOWN_TEXT = (
    "Time to close the day: tick what got done, decide on today's captures, "
    "plan tomorrow, and write one line about what you learned."
)


@jobs.handler("shutdown_nudge")
def shutdown_nudge(session: Session, payload: dict) -> None:
    """Job: the evening nudge, skipped if the day is closed or already over."""
    day = date.fromisoformat(payload["day"])
    log = session.get(DailyLog, day)
    if day != settings.today(session) or (log and log.closed_at):
        return
    send_nudges(session, [Nudge("shutdown", SHUTDOWN_TEXT)])
