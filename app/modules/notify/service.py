"""Send nudges to Telegram within a daily budget. Replies to your messages never count."""

import logging
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.kernel import clock, config, settings
from app.modules.integrations.telegram import Buttons, Telegram
from app.modules.notify import bot
from app.modules.notify.models import Notification

log = logging.getLogger(__name__)

PRIORITY = {"last_ask": 0, "block_reminder": 1}  # everything else comes after


@dataclass
class Nudge:
    """A message the system wants to send without being asked."""

    kind: str
    text: str
    buttons: Buttons = field(default_factory=list)
    item_id: int | None = None


def telegram() -> Telegram | None:
    """The bot client, or None when no token is configured. Tests replace it."""
    token = config.secret("TELEGRAM_BOT_TOKEN")
    return Telegram(token) if token else None


def sent_today(session: Session) -> int:
    """Nudges already sent today."""
    today = settings.today(session)
    return session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.day == today, Notification.status == "sent")
    )


def send_nudges(session: Session, nudges: list[Nudge]) -> list[Notification]:
    """Send the most important nudges the budget allows and hold back the rest."""
    tg, chat = telegram(), bot.chat_id(session)
    if tg is None or chat is None:
        log.info("telegram not connected, %s nudges not sent", len(nudges))
        return []
    room = settings.get(session, "nudges_per_day") - sent_today(session)
    rows = []
    for nudge in sorted(nudges, key=lambda n: PRIORITY.get(n.kind, 9)):
        row = Notification(
            day=settings.today(session),
            kind=nudge.kind,
            item_id=nudge.item_id,
            text=nudge.text,
            status="held",
            created_at=clock.now(),
        )
        if room > 0:
            row.message_id = tg.send(chat, nudge.text, nudge.buttons)["message_id"]
            row.status = "sent"
            room -= 1
        session.add(row)
        rows.append(row)
    return rows
