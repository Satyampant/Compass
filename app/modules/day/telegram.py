"""Bot commands: /today and /queue."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.kernel import clock, settings
from app.modules.autopilot import brief, resurface
from app.modules.day import service
from app.modules.learning import slots
from app.modules.learning.models import LearningItem
from app.modules.learning.telegram import short_time
from app.modules.notify import bot
from app.modules.notify.bot import Ctx


def next_block(session: Session) -> str:
    """The next learning block: the next booked item, or the next free slot."""
    now = clock.now()
    item = session.scalars(
        select(LearningItem)
        .where(LearningItem.state == "booked", LearningItem.booked_for >= now)
        .order_by(LearningItem.booked_for)
        .limit(1)
    ).first()
    if item:
        return f"Next block: {short_time(session, item.booked_for)} · {item.title}"
    return f"Next block: {short_time(session, slots.next_slot(session, now))} · nothing booked yet"


@bot.on_command("today")
def today(session: Session, ctx: Ctx) -> None:
    """The top three and the next block."""
    top = service.top_three(session, settings.today(session))
    lines = ["Today's top three", *service.top_lines(top)] if top else ["No top three yet."]
    ctx.reply("\n".join([*lines, "", next_block(session)]))


@bot.on_command("queue")
def queue(session: Session, ctx: Ctx) -> None:
    """The inbox count and today's revisit list, with answers per item."""
    waiting = session.scalar(
        select(func.count()).select_from(LearningItem).where(LearningItem.state == "inbox")
    )
    items = resurface.revisit_list(session)
    head = f"Inbox: {waiting} waiting"
    if not items:
        ctx.reply(f"{head}\nNothing back on your desk today.")
        return
    listing = brief.brief(items)
    ctx.reply(f"{head}\n{listing.text}", listing.buttons)
