"""Captures arriving by Telegram chat."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.capture import service
from app.modules.capture.models import Capture
from app.modules.learning.telegram import item_buttons
from app.modules.notify import bot
from app.modules.notify.bot import Ctx

KIND_LABELS = {"learn": "Learn later", "task": "Task", "note": "Note"}


def ago(then: datetime, now: datetime) -> str:
    """'9 days ago', 'yesterday' or 'earlier today'."""
    days = (now - then).days
    return "earlier today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago"


def on_message(session: Session, ctx: Ctx) -> None:
    """Save the message and reply with what happened."""
    message = ctx.message
    text = message.get("text") or message.get("caption") or ""
    if not text.strip():
        ctx.reply("Only links and text can be saved.")
        return
    sent_at = datetime.fromtimestamp(message["date"], UTC)
    result = service.capture(
        session,
        text=text,
        channel="telegram",
        key=f"tg:{ctx.chat_id}:{message['message_id']}",
        at=sent_at,
    )
    item = result.item
    if result.outcome == "item":
        ctx.reply(f"Saved · {item.title} · about {item.estimate_min} min")
    elif result.outcome == "duplicate":
        first = ago(item.captured_at, sent_at)
        if item.state == "inbox":
            ctx.reply(
                f"Already saved {first}. It is now top of today's list.", [item_buttons(item)]
            )
        else:
            ctx.reply(f"Already saved {first}. It is {item.state} now.")
    elif result.outcome == "pending":
        buttons = [[(label, f"cap:{k}:{result.capture.id}") for k, label in KIND_LABELS.items()]]
        ctx.reply(f"Save “{text.strip()[:60]}” as?", buttons)
    else:
        ctx.reply(f"Saved as a {result.outcome}")


@bot.on_callback("cap")
def kind_tap(session: Session, ctx: Ctx, args: list[str]) -> None:
    """Resolve plain text into the kind that was tapped."""
    kind, capture_id = args[0], int(args[1])
    cap = session.get(Capture, capture_id)
    if cap is None or kind not in service.KINDS:
        ctx.answer("Not found")
        return
    result = service.resolve(session, cap, kind)
    label = {"item": "to learn later", "task": "as a task for today", "note": "as a note"}
    ctx.edit(f"Saved {label.get(result.outcome, result.outcome)} · {cap.text.strip()[:80]}")
    ctx.answer()


bot.MESSAGE_HANDLERS.append(on_message)
