"""The learning item state machine. No other code sets LearningItem.state."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.kernel import clock, events, settings
from app.modules.learning.models import LearningItem

MOVES: dict[tuple[str, str], str] = {
    ("inbox", "book"): "booked",
    ("inbox", "let_go"): "let_go",
    ("inbox", "expire"): "expired",
    ("booked", "start"): "learning",
    ("booked", "unbook"): "inbox",
    ("booked", "let_go"): "let_go",
    ("learning", "finish"): "learned",
}
SYSTEM_ACTIONS = {"expire"}


class TransitionError(ValueError):
    """A move that is not allowed from the item's current state."""


def allowed_actions(state: str) -> list[str]:
    """The moves a person can make from a state."""
    return [a for (s, a) in MOVES if s == state and a not in SYSTEM_ACTIONS]


def create(session: Session, *, title: str, captured_at: datetime, **fields) -> LearningItem:
    """Put a new item in the inbox, with its first resurface due on day 3."""
    first = settings.get(session, "resurface_days")[0]
    fields.setdefault("estimate_min", settings.get(session, "default_estimate_min"))
    item = LearningItem(
        title=title,
        captured_at=captured_at,
        state="inbox",
        next_resurface_at=captured_at + timedelta(days=first),
        **fields,
    )
    session.add(item)
    session.flush()
    events.record(session, "item.captured", "learning_item", item.id)
    return item


def transition(
    session: Session,
    item: LearningItem,
    action: str,
    *,
    booked_for: datetime | None = None,
    note: str | None = None,
) -> LearningItem:
    """Move an item, apply what goes with the move and write an event."""
    target = MOVES.get((item.state, action))
    if target is None:
        raise TransitionError(f"cannot {action} an item that is {item.state}")
    if action == "book" and booked_for is None:
        raise TransitionError("book needs a time")
    now = clock.now()
    _APPLY[action](item, now, booked_for=booked_for, note=note)
    previous, item.state = item.state, target
    item.version += 1
    events.record(
        session, f"item.{action}", "learning_item", item.id, **{"from": previous, "to": target}
    )
    return item


def leave_desk(item: LearningItem) -> None:
    """Take the item off today's revisit list."""
    item.surfaced_at = item.pinned_at = item.last_ask_at = None


def pin_to_desk(item: LearningItem, now: datetime) -> None:
    """Put the item at the top of today's revisit list."""
    item.surfaced_at = item.pinned_at = now


def _book(item, now, *, booked_for, **_):
    item.booked_for = booked_for.astimezone(UTC)
    leave_desk(item)


def _start(item, now, **_):
    item.started_at = now


def _finish(item, now, *, note, **_):
    item.closed_at, item.note = now, note


def _unbook(item, now, **_):
    item.booked_for = None
    pin_to_desk(item, now)


def _close(item, now, **_):
    item.closed_at = now
    leave_desk(item)


_APPLY = {
    "book": _book,
    "start": _start,
    "finish": _finish,
    "unbook": _unbook,
    "let_go": _close,
    "expire": _close,
}
