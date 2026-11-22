"""Append events in the same transaction as the change that caused them."""

from sqlalchemy.orm import Session

from app.kernel import clock
from app.kernel.models import Event


def record(session: Session, kind: str, entity: str, entity_id: int | None, **data) -> None:
    """Add an event to the session. It commits or rolls back with the caller's change."""
    session.add(Event(at=clock.now(), kind=kind, entity=entity, entity_id=entity_id, data=data))
