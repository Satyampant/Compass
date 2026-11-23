"""HTTP API for the calendar connection."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.kernel import settings
from app.kernel.db import SessionDep
from app.modules.day import meetings
from app.modules.integrations import gcal
from app.modules.integrations.google import NotConnected

router = APIRouter(prefix="/v1/calendar", tags=["calendar"])


class CalendarStatus(BaseModel):
    connected: bool
    error: str | None
    calendars: list[str]


@router.get("")
def status(session: SessionDep) -> CalendarStatus:
    """Whether Google answers now, and the calendars it lists."""
    try:
        names = [c.get("summary", c["id"]) for c in gcal.connect().calendars()]
    except NotConnected as exc:
        meetings.set_status(session, False, str(exc))
        session.commit()
        return CalendarStatus(connected=False, error=str(exc), calendars=[])
    last = settings.get(session, meetings.STATUS_KEY) or {}
    return CalendarStatus(connected=True, error=last.get("error"), calendars=names)
