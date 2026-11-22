"""Capture tables: raw captures and plain notes."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base, UTCDateTime


class Capture(Base):
    """Raw input from any channel, before it becomes an item, task or note."""

    __tablename__ = "captures"

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    channel: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("learning_items.id"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    note_id: Mapped[int | None] = mapped_column(ForeignKey("notes.id"))


class Note(Base):
    """A plain-text note."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
