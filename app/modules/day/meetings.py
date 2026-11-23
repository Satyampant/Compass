"""Pull meetings from Google Calendar into read-only blocks, resuming from a saved cursor."""

import logging
from datetime import datetime, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.kernel import clock, jobs, settings
from app.modules.day.models import TimeBlock
from app.modules.integrations import gcal
from app.modules.integrations.google import NotConnected

log = logging.getLogger(__name__)

STATUS_KEY = "calendar.status"
LOOKBACK_DAYS = 7


def cursor_key(calendar_id: str) -> str:
    return f"calendar.cursor.{calendar_id}"


def set_status(session: Session, connected: bool, error: str | None = None) -> None:
    settings.put(
        session,
        STATUS_KEY,
        {"connected": connected, "error": error, "at": clock.now().isoformat()},
    )


def when(part: dict) -> datetime | None:
    """A timed event's moment, or None for an all-day event."""
    return datetime.fromisoformat(part["dateTime"]) if "dateTime" in part else None


def declined(event: dict) -> bool:
    return any(
        a.get("self") and a.get("responseStatus") == "declined" for a in event.get("attendees", [])
    )


def apply(session: Session, calendar_id: str, event: dict) -> None:
    """Insert, update or remove the block for one changed event."""
    block = session.scalars(
        select(TimeBlock).where(
            TimeBlock.calendar_id == calendar_id, TimeBlock.event_id == event["id"]
        )
    ).first()
    start, end = when(event.get("start", {})), when(event.get("end", {}))
    keep = event.get("status") != "cancelled" and start and end and not declined(event)
    if not keep:
        if block:
            session.delete(block)
        return
    if block is None:
        block = TimeBlock(
            kind="meeting",
            source="calendar",
            calendar_id=calendar_id,
            event_id=event["id"],
            created_at=clock.now(),
        )
        session.add(block)
    block.title = event.get("summary") or "Busy"
    block.start, block.end = start, end


def pull_calendar(session: Session, cal: gcal.Calendar, calendar_id: str) -> int:
    """Apply every change since the saved cursor. An expired cursor starts again from scratch."""
    cursor = settings.get(session, cursor_key(calendar_id))
    day = settings.today(session) - timedelta(days=LOOKBACK_DAYS)
    since = datetime.combine(day, time(), settings.tz(session)).isoformat()
    try:
        events, cursor = cal.events(calendar_id, sync_token=cursor, time_min=since)
    except gcal.SyncExpired:
        log.warning("sync cursor for %s expired, full resync", calendar_id)
        forget(session, calendar_id)
        events, cursor = cal.events(calendar_id, sync_token=None, time_min=since)
    for event in events:
        apply(session, calendar_id, event)
    settings.put(session, cursor_key(calendar_id), cursor)
    return len(events)


def forget(session: Session, calendar_id: str) -> None:
    """Drop a calendar's meetings and cursor, ready for a full sync."""
    session.execute(
        delete(TimeBlock).where(
            TimeBlock.source == "calendar", TimeBlock.calendar_id == calendar_id
        )
    )
    settings.put(session, cursor_key(calendar_id), None)


def pull(session: Session) -> None:
    """Pull every calendar Compass reads. A missing or revoked sign-in is recorded, not raised."""
    try:
        cal = gcal.connect()
        for calendar_id in settings.get(session, "calendar_read_ids"):
            pull_calendar(session, cal, calendar_id)
    except NotConnected as exc:
        session.rollback()
        set_status(session, False, str(exc))
        return
    set_status(session, True)


@jobs.handler("calendar_pull")
def calendar_pull(session: Session, payload: dict) -> None:
    """Job: every ten minutes while awake."""
    pull(session)
