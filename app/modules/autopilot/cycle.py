"""The calendar cycle, every ten minutes while awake: push, pull, then protect the slots."""

from sqlalchemy.orm import Session

from app.kernel import jobs
from app.modules.autopilot import protect
from app.modules.day import blocks, meetings


def run(session: Session) -> None:
    """Write pending blocks, read meeting changes, then keep learning slots off meetings."""
    blocks.push(session)
    meetings.pull(session)
    protect.run(session)
    blocks.push(session)


@jobs.handler("calendar_pull")
def calendar_pull(session: Session, payload: dict) -> None:
    """Job: one calendar cycle."""
    run(session)
