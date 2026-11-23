"""Nudges tied to the clock: a reminder before each learning block and the shutdown nudge.

Both are dropped when they come too late, so a long sleep ends in one brief, not a backlog.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.kernel import clock, jobs, settings
from app.modules.autopilot import fill
from app.modules.day import blocks
from app.modules.day.models import DailyLog, Task, TimeBlock
from app.modules.learning.models import LearningItem
from app.modules.notify.bot import Ctx, on_callback
from app.modules.notify.service import Nudge, send_nudges


def block_nudge(session: Session, block: TimeBlock, item: LearningItem) -> Nudge:
    minutes = int((block.end - block.start).total_seconds() // 60)
    when = block.start.astimezone(settings.tz(session)).strftime("%H:%M")
    lines = [f"{when} learning block: {item.title} · {minutes} min"]
    if item.url:
        lines.append(item.url)
    if item.progress_min:
        lines.append(f"Picks up at {item.progress_min} of {item.estimate_min} min")
    buttons = [[("Swap", f"block:swap:{block.id}"), ("Skip today", f"block:skip:{block.id}")]]
    return Nudge("block_reminder", "\n".join(lines), buttons, item_id=item.id)


@jobs.handler("block_reminder")
def block_reminder(session: Session, payload: dict) -> None:
    """Job: remind before a block, unless it moved, lost its item or has already begun."""
    block = session.get(TimeBlock, payload["block_id"])
    if block is None or block.start.isoformat() != payload["start"]:
        return
    if block.status != "planned" or not block.item_id or clock.now() >= block.start:
        return
    send_nudges(session, [block_nudge(session, block, session.get(LearningItem, block.item_id))])


def shutdown_text(session: Session, day: date) -> str:
    """The evening nudge, with how many of today's tasks are still open."""
    open_count = session.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.planned_date <= day, Task.done_at.is_(None), Task.dropped_at.is_(None))
    )
    if not open_count:
        return "Time to close the day. Open Compass for the shutdown."
    tasks = "1 task is" if open_count == 1 else f"{open_count} tasks are"
    return f"Time to close the day. {tasks} still open."


@jobs.handler("shutdown_nudge")
def shutdown_nudge(session: Session, payload: dict) -> None:
    """Job: the evening nudge, skipped if the day is closed or already over."""
    day = date.fromisoformat(payload["day"])
    log = session.get(DailyLog, day)
    if day != settings.today(session) or (log and log.closed_at):
        return
    send_nudges(session, [Nudge("shutdown", shutdown_text(session, day))])


@on_callback("block")
def block_tap(session: Session, ctx: Ctx, args: list[str]) -> None:
    """Swap puts the next best item in the block. Skip today frees it; the item keeps its
    booking and takes the next free slot on the next cycle."""
    action, block_id = args[0], int(args[1])
    block = session.get(TimeBlock, block_id)
    if block is None or block.status != "planned" or clock.now() >= block.end:
        ctx.answer("That block has passed")
        return
    if action == "swap":
        item = fill.swap(session, block)
        ctx.edit(f"Swapped. Now: {item.title}" if item else "Swapped out. Nothing else fits.")
    elif action == "skip":
        blocks.change(session, block, status="not_kept", item_id=None)
        ctx.edit("Skipped today. It moves to the next free learning block.")
    ctx.answer()
