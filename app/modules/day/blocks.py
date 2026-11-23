"""Compass blocks: the only code that writes to Google Calendar.

Compass writes only to the calendar it created, and only to events carrying its marker
(extendedProperties.private.compass). Meetings read from the calendar are never changed.
Changes are saved locally first (sync = push or delete) and pushed when Google answers.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, jobs, settings
from app.modules.day.models import TimeBlock
from app.modules.integrations import gcal
from app.modules.integrations.google import NotConnected

log = logging.getLogger(__name__)

COMPASS_ID_KEY = "calendar.compass_id"
MARKER = "compass"


class ReadOnly(ValueError):
    """An attempt to change something Compass did not create."""


def marked(event: dict) -> bool:
    """True when the event carries the Compass marker."""
    return event.get("extendedProperties", {}).get("private", {}).get(MARKER) == "1"


def ours(block: TimeBlock) -> None:
    """Refuse any change to a block Compass did not create."""
    if block.source != "compass":
        raise ReadOnly(f"block {block.id} comes from the calendar and is read-only")


def create(
    session: Session,
    kind: str,
    start: datetime,
    end: datetime,
    title: str,
    *,
    task_id: int | None = None,
    item_id: int | None = None,
    protected: bool = False,
    slot_at: datetime | None = None,
) -> TimeBlock:
    """A new Compass block, pushed to the calendar on the next push."""
    block = TimeBlock(
        kind=kind,
        source="compass",
        title=title,
        start=start,
        end=end,
        task_id=task_id,
        item_id=item_id,
        protected=protected,
        slot_at=slot_at,
        sync="push",
        created_at=clock.now(),
    )
    session.add(block)
    session.flush()
    request_push(session)
    schedule_reminder(session, block)
    return block


def change(session: Session, block: TimeBlock, **fields) -> TimeBlock:
    """Move, retitle or refill a Compass block."""
    ours(block)
    for name, value in fields.items():
        setattr(block, name, value)
    block.sync = "push"
    block.version += 1
    request_push(session)
    schedule_reminder(session, block)
    return block


def remove(session: Session, block: TimeBlock) -> None:
    """Delete a Compass block, and its event once Google answers."""
    ours(block)
    if block.event_id is None:
        session.delete(block)
        return
    block.sync = "delete"
    request_push(session)


def schedule_reminder(session: Session, block: TimeBlock) -> None:
    """One reminder job per learning block and start time, due before it starts. Empty
    protected slots get one too: it suggests the shortest item in the inbox."""
    wanted = block.item_id or block.protected
    if block.kind != "learning" or block.status != "planned" or not wanted:
        return
    lead = timedelta(minutes=settings.get(session, "block_reminder_min"))
    start = block.start.astimezone(UTC).isoformat()
    key = f"block_reminder:{block.id}:{start}"
    jobs.enqueue(
        session,
        "block_reminder",
        block.start - lead,
        key=key,
        block_id=block.id,
        start=start,
    )


def request_push(session: Session) -> None:
    """Ask the scheduler to push soon. One push job per minute at most."""
    now = clock.now().replace(second=0, microsecond=0)
    jobs.enqueue(session, "calendar_push", now, key=f"calendar_push:{now.isoformat()}")


def compass_calendar(session: Session, cal: gcal.Calendar) -> str:
    """The id of the calendar Compass writes to, created on first use."""
    cal_id = settings.get(session, COMPASS_ID_KEY)
    if cal_id is None:
        name, tz = settings.get(session, "calendar_name"), settings.get(session, "timezone")
        cal_id = cal.create_calendar(name, tz)["id"]
        settings.put(session, COMPASS_ID_KEY, cal_id)
    return cal_id


def event_body(block: TimeBlock, item_url: str | None = None) -> dict:
    body = {
        "summary": block.title,
        "start": {"dateTime": block.start.isoformat()},
        "end": {"dateTime": block.end.isoformat()},
        "extendedProperties": {"private": {MARKER: "1", "block_id": str(block.id)}},
    }
    if item_url:
        body["description"] = item_url
    return body


def existing(cal: gcal.Calendar, cal_id: str, block: TimeBlock) -> dict | None:
    """The block's event, or None if it was deleted in Google. A foreign event is returned as
    is, so the marker check refuses it."""
    if not block.event_id:
        return None
    try:
        event = cal.get_event(block.calendar_id or cal_id, block.event_id)
    except gcal.NotFound:
        return None
    return None if event.get("status") == "cancelled" and marked(event) else event


def push_one(session: Session, cal: gcal.Calendar, cal_id: str, block: TimeBlock) -> None:
    """Write one pending block. An event that lost its marker is left alone."""
    ours(block)
    event = existing(cal, cal_id, block)
    if block.event_id and event is None:
        if block.sync == "delete":
            session.delete(block)
            return
        block.event_id = None
    if block.event_id:
        if block.calendar_id != cal_id or not marked(event):
            log.warning("block %s points at an event without the Compass marker", block.id)
            block.sync = "conflict"
            return
        if block.sync == "delete":
            cal.delete_event(cal_id, block.event_id)
            session.delete(block)
            return
        cal.patch_event(cal_id, block.event_id, event_body(block, _url(session, block)))
    elif block.sync == "push":
        event = cal.insert_event(cal_id, event_body(block, _url(session, block)))
        block.calendar_id, block.event_id = cal_id, event["id"]
    block.sync = "synced"


def _url(session: Session, block: TimeBlock) -> str | None:
    from app.modules.learning.models import LearningItem

    item = session.get(LearningItem, block.item_id) if block.item_id else None
    return item.url if item else None


def push(session: Session) -> int:
    """Write every pending Compass block. Without a sign-in they stay pending."""
    pending = list(
        session.scalars(
            select(TimeBlock).where(
                TimeBlock.source == "compass", TimeBlock.sync.in_(("push", "delete"))
            )
        )
    )
    if not pending:
        return 0
    try:
        cal = gcal.connect()
        cal_id = compass_calendar(session, cal)
        for block in pending:
            push_one(session, cal, cal_id, block)
    except NotConnected as exc:
        log.info("calendar not connected, %s blocks wait: %s", len(pending), exc)
    return len(pending)


@jobs.handler("calendar_push")
def calendar_push(session: Session, payload: dict) -> None:
    """Job: write pending blocks."""
    push(session)
