from datetime import UTC, datetime

import pytest

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
