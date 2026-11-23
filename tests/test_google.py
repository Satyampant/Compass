import httpx
import pytest

from app.modules.integrations import gcal, google


@pytest.fixture
def keychain(monkeypatch):
    store = {}
    monkeypatch.setattr(google.keyring, "get_password", lambda s, u: store.get((s, u)))
    monkeypatch.setattr(google.keyring, "set_password", lambda s, u, p: store.update({(s, u): p}))
    monkeypatch.setattr(google.keyring, "delete_password", lambda s, u: store.pop((s, u)))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    return store


def token_server(calls, status=200):
    def handle(request):
        calls.append(request)
        if status != 200:
            return httpx.Response(status, json={"error": "invalid_grant"})
        return httpx.Response(200, json={"access_token": f"at{len(calls)}", "expires_in": 3600})

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_not_signed_in(keychain):
    with pytest.raises(google.NotConnected, match="not signed in"):
        google.Tokens(token_server([])).get()


def test_refresh_token_from_keychain_survives_restart(keychain):
    google.save_refresh_token("rt")
    calls = []
    first = google.Tokens(token_server(calls))
    assert first.get() == "at1" and first.get() == "at1"
    assert len(calls) == 1 and b"refresh_token=rt" in calls[0].content
    after_restart = google.Tokens(token_server(calls))
    assert after_restart.get() == "at2"


def test_revoked_token_means_not_connected(keychain):
    google.save_refresh_token("rt")
    with pytest.raises(google.NotConnected, match="invalid_grant"):
        google.Tokens(token_server([], status=400)).get()


def test_calendar_list_and_401_retry(keychain):
    google.save_refresh_token("rt")
    seen = []

    def api(request):
        seen.append(request.headers["Authorization"])
        if len(seen) == 1:
            return httpx.Response(401)
        return httpx.Response(200, json={"items": [{"id": "primary", "summary": "Me"}]})

    cal = gcal.Calendar(
        google.Tokens(token_server([])), httpx.Client(transport=httpx.MockTransport(api))
    )
    assert cal.calendars() == [{"id": "primary", "summary": "Me"}]
    assert seen == ["Bearer at1", "Bearer at2"]


def test_events_pages_and_expired_cursor(keychain):
    google.save_refresh_token("rt")

    def api(request):
        params = dict(request.url.params)
        if params.get("syncToken") == "old":
            return httpx.Response(410)
        if "pageToken" not in params:
            return httpx.Response(200, json={"items": [{"id": "a"}], "nextPageToken": "p2"})
        return httpx.Response(200, json={"items": [{"id": "b"}], "nextSyncToken": "s1"})

    cal = gcal.Calendar(
        google.Tokens(token_server([])), httpx.Client(transport=httpx.MockTransport(api))
    )
    items, cursor = cal.events("primary", sync_token=None, time_min="2026-11-16T00:00:00Z")
    assert [i["id"] for i in items] == ["a", "b"] and cursor == "s1"
    with pytest.raises(gcal.SyncExpired):
        cal.events("primary", sync_token="old", time_min=None)
