"""The calendar cycle, every ten minutes while awake: push, pull, protect and fill the slots."""

from sqlalchemy.orm import Session

from app.kernel import jobs, settings
from app.modules.autopilot import fill, protect
from app.modules.day import blocks, meetings


def run(session: Session) -> None:
    """Push pending blocks, read meeting changes, move slots off meetings and fill them.

    Slots are protected only on a connected calendar. Without one, Compass works as before.
    """
    blocks.push(session)
    meetings.pull(session)
    if not (settings.get(session, meetings.STATUS_KEY) or {}).get("connected"):
        return
    protect.run(session)
    fill.run(session)
    blocks.push(session)


@jobs.handler("calendar_pull")
def calendar_pull(session: Session, payload: dict) -> None:
    """Job: one calendar cycle."""
    run(session)
