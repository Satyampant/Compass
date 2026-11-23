"""The learning item state machine. No other code sets LearningItem.state."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
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
    ("learning", "return"): "booked",
}
NEEDS_TIME = {"book", "return"}
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
    if action in NEEDS_TIME and booked_for is None:
        raise TransitionError(f"{action} needs a time")
    if action == "finish" and not (note or "").strip():
        raise TransitionError(
            "marking learned needs one line: what you took from it or did with it"
        )
    if action == "start":
        check_room(session)
    now = clock.now()
    today = settings.today(session)
    _APPLY[action](item, now, booked_for=booked_for, note=note, today=today)
    previous, item.state = item.state, target
    item.version += 1
    events.record(
        session, f"item.{action}", "learning_item", item.id, **{"from": previous, "to": target}
    )
    return item


def check_room(session: Session) -> None:
    """Refuse a third item in Learning. Finish or return one first."""
    limit = settings.get(session, "max_in_learning")
    busy = session.scalar(
        select(func.count()).select_from(LearningItem).where(LearningItem.state == "learning")
    )
    if busy >= limit:
        raise TransitionError(f"{limit} items are in Learning already. Finish or return one first")


def leave_desk(item: LearningItem) -> None:
    """Take the item off the revisit list after a decision."""
    item.surfaced_at = item.pinned_at = item.last_ask_at = item.shown_on = None


def pin_to_desk(item: LearningItem, now: datetime, today: date) -> None:
    """Put the item at the top of today's revisit list."""
    item.surfaced_at = item.pinned_at = now
    item.shown_on = today


def _book(item, now, *, booked_for, **_):
    item.booked_for = booked_for.astimezone(UTC)
    leave_desk(item)


def _start(item, now, **_):
    item.started_at = now


def _finish(item, now, *, note, **_):
    item.closed_at, item.note = now, note.strip()


def _return(item, now, *, booked_for, **_):
    item.booked_for = booked_for.astimezone(UTC)


def _unbook(item, now, *, today, **_):
    item.booked_for = None
    pin_to_desk(item, now, today)


def _close(item, now, **_):
    item.closed_at = now
    leave_desk(item)


_APPLY = {
    "book": _book,
    "start": _start,
    "finish": _finish,
    "return": _return,
    "unbook": _unbook,
    "let_go": _close,
    "expire": _close,
}
