"""Telegram Bot API adapter over httpx. No business rules here."""

import httpx

Buttons = list[list[tuple[str, str]]]  # rows of (label, callback data)


class TelegramError(RuntimeError):
    """The Bot API answered with ok=false."""


class Telegram:
    """A minimal Bot API client: long polling, messages with buttons, callback answers."""

    def __init__(self, token: str, client: httpx.Client | None = None):
        self.base = f"https://api.telegram.org/bot{token}"
        self.client = client or httpx.Client(
            timeout=30
        )  # long poll is 25s; a dead socket after sleep fails fast

    def call(self, method: str, **params):
        """Call a Bot API method and return its result."""
        body = self.client.post(f"{self.base}/{method}", json=params).json()
        if not body.get("ok"):
            raise TelegramError(f"{method}: {body.get('description')}")
        return body["result"]

    def get_me(self) -> dict:
        return self.call("getMe")

    def get_updates(self, offset: int | None, timeout: int = 25) -> list[dict]:
        """Wait up to timeout seconds for updates after offset. Earlier ones are confirmed."""
        params = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            params["offset"] = offset
        return self.call("getUpdates", **params)

    def send(self, chat_id: int, text: str, buttons: Buttons | None = None) -> dict:
        params = {"chat_id": chat_id, "text": text, "link_preview_options": {"is_disabled": True}}
        if buttons:
            params["reply_markup"] = keyboard(buttons)
        return self.call("sendMessage", **params)

    def edit(self, chat_id: int, message_id: int, text: str, buttons: Buttons | None = None):
        params = {"chat_id": chat_id, "message_id": message_id, "text": text}
        params["reply_markup"] = keyboard(buttons or [])
        return self.call("editMessageText", **params)

    def answer(self, callback_id: str, text: str | None = None) -> None:
        params = {"callback_query_id": callback_id}
        if text:
            params["text"] = text
        self.call("answerCallbackQuery", **params)


def keyboard(buttons: Buttons) -> dict:
    """Inline keyboard markup from rows of (label, data)."""
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": data} for label, data in row] for row in buttons
        ]
    }
