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


class FakeCalendar:
    """An in-memory Google Calendar. Like the real scope, it refuses writes to calendars
    this app did not create. Each change bumps a counter that sync cursors point into."""

    def __init__(self):
        self.store: dict[str, dict[str, dict]] = {"primary": {}}
        self.changes: dict[str, list[tuple[int, str]]] = {"primary": []}
        self.owned: set[str] = set()
        self.writes: list[tuple] = []
        self.counter = 0
        self.expired: set[str] = set()

    def _touch(self, cal, event_id):
        self.counter += 1
        self.changes.setdefault(cal, []).append((self.counter, event_id))

    def put(self, cal, event):
        """A change made by someone else, straight in Google Calendar."""
        self.store.setdefault(cal, {})[event["id"]] = event
        self._touch(cal, event["id"])

    def cancel(self, cal, event_id):
        self.store[cal][event_id]["status"] = "cancelled"
        self._touch(cal, event_id)

    def calendars(self):
        return [{"id": c, "summary": c} for c in self.store]

    def create_calendar(self, summary, time_zone):
        cal = f"compass-{len(self.owned) + 1}"
        self.owned.add(cal)
        self.store[cal] = {}
        self.writes.append(("create_calendar", summary))
        return {"id": cal, "summary": summary}

    def events_since(self, cal, since):
        ids = {e for n, e in self.changes.get(cal, []) if n > since}
        return [self.store[cal][e] for e in ids]

    def events(self, cal, *, sync_token, time_min):
        from app.modules.integrations.gcal import SyncExpired

        if sync_token in self.expired:
            raise SyncExpired(cal)
        since = int(sync_token) if sync_token else 0
        items = self.events_since(cal, since)
        if not sync_token:
            items = [e for e in items if e.get("status") != "cancelled"]
        return items, str(self.counter)

    def _check(self, cal):
        if cal not in self.owned:
            raise PermissionError(f"403: cannot write to {cal}")

    def get_event(self, cal, event_id):
        from app.modules.integrations.gcal import NotFound

        if event_id not in self.store.get(cal, {}):
            raise NotFound(event_id)
        return self.store[cal][event_id]

    def insert_event(self, cal, event):
        self._check(cal)
        event = {**event, "id": f"ev{self.counter + 1}"}
        self.writes.append(("insert", cal, event["id"]))
        self.put(cal, event)
        return event

    def patch_event(self, cal, event_id, event):
        self._check(cal)
        self.writes.append(("patch", cal, event_id))
        self.store[cal][event_id].update(event)
        self._touch(cal, event_id)
        return self.store[cal][event_id]

    def delete_event(self, cal, event_id):
        self._check(cal)
        self.writes.append(("delete", cal, event_id))
        self.cancel(cal, event_id)
