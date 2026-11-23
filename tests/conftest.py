from datetime import UTC, datetime

import pytest

import app.handlers  # noqa: F401
from app.kernel import clock, db, migrate


@pytest.fixture
def session(tmp_path):
    """A session on a fresh database built from migrations."""
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    migrate.upgrade()
    with db.SessionLocal() as s:
        yield s


@pytest.fixture
def fake_clock():
    """Replace the app clock with one that moves only when told to."""
    fake = clock.FakeClock(datetime(2026, 11, 23, 0, 30, tzinfo=UTC))  # 06:00 IST, Monday
    clock.use(fake)
    yield fake
    clock.use(clock.Clock())


@pytest.fixture
def client(session):
    """An API client on the test database. Background threads are not started."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Page fetches answer 404 unless a test installs its own fake web."""
    import httpx

    from app.modules.capture import enrich

    offline = httpx.MockTransport(lambda request: httpx.Response(404))
    monkeypatch.setattr(enrich, "make_client", lambda: httpx.Client(transport=offline))


@pytest.fixture(autouse=True)
def backups_in_tmp(monkeypatch, tmp_path):
    """Scheduler ticks in tests write backups to a temporary folder, never into data/."""
    from app.kernel import backup

    monkeypatch.setattr(backup, "backup_dir", lambda session: tmp_path / "backups")


@pytest.fixture(autouse=True)
def no_calendar(monkeypatch):
    """No test reaches Google or the Keychain. The calendar reads as not signed in."""
    from app.modules.integrations import gcal
    from app.modules.integrations.google import NotConnected

    def refuse():
        raise NotConnected("not signed in to Google")

    monkeypatch.setattr(gcal, "connect", refuse)


@pytest.fixture
def calendar(monkeypatch):
    """An in-memory Google Calendar in place of the real one."""
    from app.modules.integrations import gcal
    from tests.fakes import FakeCalendar

    fake = FakeCalendar()
    monkeypatch.setattr(gcal, "connect", lambda: fake)
    return fake
