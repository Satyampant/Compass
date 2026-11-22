"""Test doubles for outside services."""


class FakeTelegram:
    """Records what the bot sends and serves queued updates."""

    def __init__(self):
        self.updates: list[dict] = []
        self.sent: list[dict] = []
        self.answers: list[tuple[str, str | None]] = []
        self.edits: list[dict] = []
        self.next_id = 1
        self.fail_sends = False

    def get_updates(self, offset, timeout=25):
        return [u for u in self.updates if offset is None or u["update_id"] >= offset]

    def send(self, chat_id, text, buttons=None):
        if self.fail_sends:
            raise RuntimeError("network down")
        self.sent.append({"chat_id": chat_id, "text": text, "buttons": buttons or []})
        self.next_id += 1
        return {"message_id": self.next_id}

    def edit(self, chat_id, message_id, text, buttons=None):
        self.edits.append({"message_id": message_id, "text": text, "buttons": buttons or []})

    def answer(self, callback_id, text=None):
        self.answers.append((callback_id, text))

    def push_message(self, chat_id, text, date=1795400000):
        uid = len(self.updates) + 100
        self.updates.append(
            {
                "update_id": uid,
                "message": {
                    "message_id": uid,
                    "date": date,
                    "chat": {"id": chat_id},
                    "from": {"id": chat_id},
                    "text": text,
                },
            }
        )

    def push_tap(self, chat_id, data, message_id=1):
        uid = len(self.updates) + 100
        self.updates.append(
            {
                "update_id": uid,
                "callback_query": {
                    "id": f"cb{uid}",
                    "data": data,
                    "from": {"id": chat_id},
                    "message": {"message_id": message_id, "chat": {"id": chat_id}},
                },
            }
        )

    def texts(self):
        return [m["text"] for m in self.sent]
