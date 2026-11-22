"""Route Telegram updates: lock to one chat, dispatch messages and button taps.

Handlers stage replies in an outbox. Replies are sent only after the database commit,
and the update is confirmed to Telegram (offset moves on) in that same commit.
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.kernel import clock, db, settings
from app.modules.integrations.telegram import Buttons, Telegram

log = logging.getLogger(__name__)

CHAT_KEY = "telegram.chat_id"
OFFSET_KEY = "telegram.offset"
LAST_POLL_KEY = "telegram.last_poll_at"


@dataclass
class Ctx:
    """One update being handled, and the replies it will send."""

    chat_id: int
    message: dict | None = None
    callback: dict | None = None
    outbox: list[Callable[[Telegram], object]] = field(default_factory=list)

    def reply(self, text: str, buttons: Buttons | None = None) -> None:
        self.outbox.append(lambda tg: tg.send(self.chat_id, text, buttons))

    def edit(self, text: str, buttons: Buttons | None = None) -> None:
        message_id = self.callback["message"]["message_id"]
        self.outbox.append(lambda tg: tg.edit(self.chat_id, message_id, text, buttons))

    def answer(self, text: str | None = None) -> None:
        callback_id = self.callback["id"]
        self.outbox.append(lambda tg: tg.answer(callback_id, text))


Handler = Callable[[Session, Ctx, list[str]], None]
CALLBACKS: dict[str, Handler] = {}
MESSAGE_HANDLERS: list[Callable[[Session, Ctx], None]] = []


def on_callback(prefix: str) -> Callable[[Handler], Handler]:
    """Register a handler for button data starting with prefix, as in 'item:book:7'."""

    def wrap(fn: Handler) -> Handler:
        CALLBACKS[prefix] = fn
        return fn

    return wrap


def handle_update(session: Session, update: dict) -> Ctx | None:
    """Apply one update to the database. Returns the context with replies to send."""
    message, callback = update.get("message"), update.get("callback_query")
    source = message or (callback or {}).get("message")
    if not source:
        return None
    ctx = Ctx(chat_id=source["chat"]["id"], message=message, callback=callback)
    locked = settings.get(session, CHAT_KEY)
    if message and (message.get("text") or "").startswith("/start"):
        _start(session, ctx, locked)
        return ctx
    if locked != ctx.chat_id:
        log.warning("ignored update from chat %s", ctx.chat_id)
        return None
    if callback:
        prefix, *args = callback.get("data", "").split(":")
        handler = CALLBACKS.get(prefix)
        if handler:
            handler(session, ctx, args)
        else:
            ctx.answer("Unknown button")
    elif message:
        for fn in MESSAGE_HANDLERS:
            fn(session, ctx)
    return ctx


def _start(session: Session, ctx: Ctx, locked: int | None) -> None:
    if locked is None:
        settings.put(session, CHAT_KEY, ctx.chat_id)
        ctx.reply("Compass is connected to this chat. Share any link here and it will be saved.")
    elif locked == ctx.chat_id:
        ctx.reply("Compass is already connected to this chat.")
    else:
        log.warning("refused /start from chat %s", ctx.chat_id)


def process(tg: Telegram, update: dict) -> None:
    """Store an update and confirm it in one commit, then send its replies."""
    with db.SessionLocal() as s:
        ctx = handle_update(s, update)
        settings.put(s, OFFSET_KEY, update["update_id"] + 1)
        s.commit()
    for send in ctx.outbox if ctx else []:
        try:
            send(tg)
        except Exception:
            log.exception("telegram send failed")


def poll_once(tg: Telegram, timeout: int = 25) -> int:
    """Fetch and process waiting updates in order. Returns how many were processed."""
    with db.SessionLocal() as s:
        offset = settings.get(s, OFFSET_KEY)
    updates = tg.get_updates(offset, timeout=timeout)
    with db.SessionLocal() as s:
        settings.put(s, LAST_POLL_KEY, clock.now().isoformat())
        s.commit()
    for update in updates:
        process(tg, update)
    return len(updates)


def chat_id(session: Session) -> int | None:
    """The one chat the bot talks to, once locked."""
    return settings.get(session, CHAT_KEY)


class Poller(threading.Thread):
    """Long-polls Telegram until stopped. A failed update is not confirmed, so it comes again."""

    def __init__(self, tg: Telegram):
        super().__init__(name="telegram", daemon=True)
        self.tg = tg
        self.stopped = threading.Event()

    def run(self) -> None:
        while not self.stopped.is_set():
            try:
                poll_once(self.tg)
            except Exception:
                log.exception("telegram poll failed")
                self.stopped.wait(5)

    def stop(self) -> None:
        self.stopped.set()
