"""Day tables: tasks and daily logs."""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base, UTCDateTime


class Task(Base):
    """A piece of work planned for a date."""

    __tablename__ = "tasks"
    __table_args__ = (
        Index(
            "uq_task_rank_per_day",
            "planned_date",
            "top_rank",
            unique=True,
            sqlite_where=text("top_rank IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    estimate_min: Mapped[int] = mapped_column(Integer, default=30)
    planned_date: Mapped[date] = mapped_column(index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), index=True)
    top_rank: Mapped[int | None] = mapped_column(Integer)
    done_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    dropped_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=1)


class DailyLog(Base):
    """One row per local date: when it was planned and closed."""

    __tablename__ = "daily_logs"

    day: Mapped[date] = mapped_column(primary_key=True)
    planned_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    learned_line: Mapped[str | None] = mapped_column(Text)


class TimeBlock(Base):
    """A span of a day: a meeting read from the calendar, or a task or learning block Compass owns.

    Meetings have source "calendar" and are read-only. A block holds a task or an item, never
    both. sync tells the calendar writer what to do with a Compass block: synced, push or delete.
    """

    __tablename__ = "time_blocks"
    __table_args__ = (
        Index("uq_block_event", "calendar_id", "event_id", unique=True),
        CheckConstraint("task_id IS NULL OR item_id IS NULL", name="ck_block_one_holder"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(12))
    source: Mapped[str] = mapped_column(String(12))
    title: Mapped[str] = mapped_column(Text)
    start: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    end: Mapped[datetime] = mapped_column(UTCDateTime)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("learning_items.id"), index=True)
    protected: Mapped[bool] = mapped_column(default=False)
    slot_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    status: Mapped[str] = mapped_column(String(12), default="planned")
    calendar_id: Mapped[str | None] = mapped_column(Text)
    event_id: Mapped[str | None] = mapped_column(Text)
    sync: Mapped[str] = mapped_column(String(8), default="synced")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=1)
