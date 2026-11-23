"""HTTP API for the calendar connection: status, the calendar list and a full resync."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import update

from app.kernel import clock, settings
from app.kernel.db import SessionDep
from app.modules.day import meetings
from app.modules.day.models import TimeBlock
from app.modules.integrations import gcal
from app.modules.integrations.google import NotConnected

router = APIRouter(prefix="/v1/calendar", tags=["calendar"])


class CalendarStatus(BaseModel):
    connected: bool
    ever_connected: bool = False
    error: str | None
    at: str | None


def current(session) -> CalendarStatus:
    last = settings.get(session, meetings.STATUS_KEY)
    if last is None:
        return CalendarStatus(connected=False, error="not checked yet", at=None)
    return CalendarStatus(**last)


@router.get("")
def status(session: SessionDep) -> CalendarStatus:
    """The result of the last calendar cycle. Cheap: no call to Google."""
    return current(session)


@router.get("/calendars")
def calendars() -> list[str]:
    """The calendars Google lists for this sign-in."""
    try:
        return [c.get("summary", c["id"]) for c in gcal.connect().calendars()]
    except NotConnected:
        return []


@router.post("/resync")
def resync(session: SessionDep) -> CalendarStatus:
    """Rebuild calendar data from scratch: forget meetings and cursors, write every upcoming
    Compass block again, then run one calendar cycle."""
    from app.modules.autopilot import cycle

    for calendar_id in settings.get(session, "calendar_read_ids"):
        meetings.forget(session, calendar_id)
    session.execute(
        update(TimeBlock)
        .where(
            TimeBlock.source == "compass",
            TimeBlock.end > clock.now(),
            TimeBlock.sync.in_(("synced", "conflict")),
        )
        .values(sync="push")
    )
    cycle.run(session)
    session.commit()
    return current(session)
