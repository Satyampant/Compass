"""The morning brief: today's top three and revisit list on the phone. Last asks go alone."""

from sqlalchemy.orm import Session

from app.kernel import clock, jobs, settings
from app.modules.autopilot import resurface
from app.modules.capture.telegram import ago
from app.modules.day import service as day
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


def brief(items: list[LearningItem], top: list[str] = ()) -> Nudge:
    """One message: the top three first, then the revisit list with a row of answers per item."""
    lines = ["Today's top three", *top, ""] if top else []
    if items:
        lines.append(f"Back on your desk: {len(items)} item{'s' if len(items) > 1 else ''}")
    lines += [f"{n}. {i.title} · {i.estimate_min} min" for n, i in enumerate(items, 1)]
    rows = [
        [(f"{n} Book", f"item:book:{i.id}"), (f"{n} Let go", f"item:let_go:{i.id}")]
        for n, i in enumerate(items, 1)
    ]
    return Nudge("brief", "\n".join(lines).strip(), rows)


def build(session: Session) -> list[Nudge]:
    """The nudges for this morning, nothing if there is no top three and no revisit list."""
    items = resurface.revisit_list(session)
    top = day.top_lines(day.top_three(session, settings.today(session)))
    asks = [i for i in items if i.last_ask_at is not None]
    rest = [i for i in items if i.last_ask_at is None]
    lead = [brief(rest, top)] if rest or top else []
    return lead + [last_ask(i) for i in asks]


@jobs.handler("morning_brief")
def morning_brief(session: Session, payload: dict) -> None:
    """Job: send this morning's nudges."""
    send_nudges(session, build(session))
