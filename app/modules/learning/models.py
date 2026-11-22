"""The learning_items table."""

from datetime import datetime

from sqlalchemy import Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base, UTCDateTime

OPEN_STATES = ("inbox", "booked", "learning")


class LearningItem(Base):
    """Something saved to learn. Its state changes only through lifecycle.transition."""

    __tablename__ = "learning_items"
    __table_args__ = (
        Index(
            "uq_open_url_hash",
            "url_hash",
            unique=True,
            sqlite_where=text("state IN ('inbox', 'booked', 'learning') AND url_hash IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    url_hash: Mapped[str | None] = mapped_column(String(64))
    source_type: Mapped[str] = mapped_column(String(16), default="article")
    estimate_min: Mapped[int] = mapped_column(Integer, default=20)
    state: Mapped[str] = mapped_column(String(16), default="inbox", index=True)
    captured_at: Mapped[datetime] = mapped_column(UTCDateTime)
    resurface_count: Mapped[int] = mapped_column(Integer, default=0)
    next_resurface_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    surfaced_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    pinned_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_ask_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    booked_for: Mapped[datetime | None] = mapped_column(UTCDateTime)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
