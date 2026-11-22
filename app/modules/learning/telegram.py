"""Book and Let go buttons on items, wherever the bot shows them."""

from sqlalchemy.orm import Session

from app.kernel import clock, settings
from app.modules.learning import lifecycle, slots
from app.modules.learning.models import LearningItem
from app.modules.notify.bot import Ctx, on_callback


def item_buttons(item: LearningItem) -> list[tuple[str, str]]:
    """One row of answers for an item in the inbox."""
    return [("Book", f"item:book:{item.id}"), ("Let go", f"item:let_go:{item.id}")]


def short_time(session: Session, at) -> str:
    """A local time like 'Mon 16:00'."""
    return at.astimezone(settings.tz(session)).strftime("%a %H:%M")


@on_callback("item")
def item_tap(session: Session, ctx: Ctx, args: list[str]) -> None:
    """Apply a Book or Let go tap and update the message."""
    action, item_id = args[0], int(args[1])
    item = session.get(LearningItem, item_id)
    if item is None or action not in ("book", "let_go"):
        ctx.answer("Not found")
        return
    try:
        if action == "book":
            when = slots.next_slot(session, clock.now())
            lifecycle.transition(session, item, "book", booked_for=when)
            ctx.edit(f"Booked for {short_time(session, when)} · {item.title}")
        else:
            lifecycle.transition(session, item, "let_go")
            ctx.edit(f"Let go · {item.title}")
        ctx.answer()
    except lifecycle.TransitionError:
        ctx.answer(f"Already {item.state.replace('_', ' ')}")
