"""The morning brief: today's revisit list on the phone, last asks as their own messages."""

from sqlalchemy.orm import Session

from app.kernel import clock, jobs
from app.modules.autopilot import resurface
from app.modules.capture.telegram import ago
from app.modules.learning.models import LearningItem
from app.modules.notify.service import Nudge, send_nudges


def last_ask(item: LearningItem) -> Nudge:
    """Day 21: keep it or let it go."""
    return Nudge(
        "last_ask",
        f"Saved {ago(item.captured_at, clock.now())}: {item.title}. Keep it or let it go?",
        [[("Book", f"item:book:{item.id}"), ("Let go", f"item:let_go:{item.id}")]],
        item_id=item.id,
    )


def brief(items: list[LearningItem]) -> Nudge:
    """One message listing the rest of today's list, with a row of answers per item."""
    lines = [f"Back on your desk: {len(items)} item{'s' if len(items) > 1 else ''}"]
    lines += [f"{n}. {i.title} · {i.estimate_min} min" for n, i in enumerate(items, 1)]
    rows = [
        [(f"{n} Book", f"item:book:{i.id}"), (f"{n} Let go", f"item:let_go:{i.id}")]
        for n, i in enumerate(items, 1)
    ]
    return Nudge("brief", "\n".join(lines), rows)


def build(session: Session) -> list[Nudge]:
    """The nudges for this morning, nothing if the list is empty."""
    items = resurface.revisit_list(session)
    asks = [i for i in items if i.last_ask_at is not None]
    rest = [i for i in items if i.last_ask_at is None]
    return [last_ask(i) for i in asks] + ([brief(rest)] if rest else [])


@jobs.handler("morning_brief")
def morning_brief(session: Session, payload: dict) -> None:
    """Job: send this morning's nudges."""
    send_nudges(session, build(session))
