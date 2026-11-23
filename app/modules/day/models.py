"""Day tables: tasks and daily logs."""

from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, Integer, Text, text
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
