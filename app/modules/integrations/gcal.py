"""Google Calendar over plain HTTP. No business rules live here."""

import os

import httpx

from app.modules.integrations.google import NotConnected, Tokens

BASE = "https://www.googleapis.com/calendar/v3"


class SyncExpired(RuntimeError):
    """The sync cursor is no longer valid. Start a full sync."""


class NotFound(RuntimeError):
    """The event or calendar does not exist."""


class Calendar:
    """The Calendar API calls Compass uses."""

    def __init__(self, tokens: Tokens | None = None, http: httpx.Client | None = None):
        self.tokens = tokens or Tokens()
        self.http = http or httpx.Client(timeout=30)

    def call(self, method: str, path: str, **kw) -> dict:
        for attempt in (1, 2):
            headers = {"Authorization": f"Bearer {self.tokens.get()}"}
            r = self.http.request(method, f"{BASE}{path}", headers=headers, **kw)
            if r.status_code == 401 and attempt == 1:
                self.tokens.access = None
                continue
            break
        if r.status_code == 401:
            raise NotConnected("Google refused the access token")
        if r.status_code == 410:
            raise SyncExpired(path)
        if r.status_code == 404:
            raise NotFound(path)
        r.raise_for_status()
        return r.json() if r.content else {}

    def calendars(self) -> list[dict]:
        return self.call("GET", "/users/me/calendarList").get("items", [])

    def create_calendar(self, summary: str, time_zone: str) -> dict:
        return self.call("POST", "/calendars", json={"summary": summary, "timeZone": time_zone})

    def events(
        self, calendar_id: str, *, sync_token: str | None, time_min: str | None
    ) -> tuple[list[dict], str]:
        """Every changed event since sync_token (or all from time_min) and the next cursor."""
        params = {"singleEvents": "true", "maxResults": "250", "showDeleted": "true"}
        if sync_token:
            params["syncToken"] = sync_token
        elif time_min:
            params["timeMin"] = time_min
        items, page = [], None
        while True:
            body = self.call(
                "GET",
                f"/calendars/{calendar_id}/events",
                params={**params, **({"pageToken": page} if page else {})},
            )
            items += body.get("items", [])
            page = body.get("nextPageToken")
            if not page:
                return items, body["nextSyncToken"]

    def get_event(self, calendar_id: str, event_id: str) -> dict:
        return self.call("GET", f"/calendars/{calendar_id}/events/{event_id}")

    def insert_event(self, calendar_id: str, event: dict) -> dict:
        return self.call("POST", f"/calendars/{calendar_id}/events", json=event)

    def patch_event(self, calendar_id: str, event_id: str, event: dict) -> dict:
        return self.call("PATCH", f"/calendars/{calendar_id}/events/{event_id}", json=event)

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        self.call("DELETE", f"/calendars/{calendar_id}/events/{event_id}")


def connect() -> Calendar:
    """The live calendar client. COMPASS_GOOGLE=0 turns it off. Tests replace this with a fake."""
    if os.environ.get("COMPASS_GOOGLE") == "0":
        raise NotConnected("Google Calendar is turned off for this process")
    return Calendar()
