"""SQLite engine, sessions and shared column types."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_URL = f"sqlite:///{ROOT / 'data' / 'compass.db'}"


class UTCDateTime(TypeDecorator):
    """Store aware datetimes as naive UTC and return them aware."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        return None if value is None else value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    """Base class for all tables."""


def make_engine(url: str) -> Engine:
    """Create an engine with write-ahead logging and foreign keys on."""
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})

    @event.listens_for(engine, "connect")
    def _pragmas(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=15000")
        cur.close()

    return engine


engine: Engine = make_engine(os.environ.get("COMPASS_DB_URL", DEFAULT_URL))
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def configure(url: str) -> Engine:
    """Point the app at another database, used by tests and tools."""
    global engine
    engine = make_engine(url)
    SessionLocal.configure(bind=engine)
    return engine


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with SessionLocal() as session:
        yield session
