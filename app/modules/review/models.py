"""Review tables: each day's numbers, and each week's review."""

from datetime import date, datetime

from sqlalchemy import JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base, UTCDateTime


class DayStats(Base):
    """A day's numbers, written by the rollup and replaced if it runs again."""

    __tablename__ = "day_stats"

    day: Mapped[date] = mapped_column(primary_key=True)
    aligned_min: Mapped[int] = mapped_column(Integer)
    planned_min: Mapped[int] = mapped_column(Integer)
    top_planned: Mapped[int] = mapped_column(Integer)
    top_done: Mapped[int] = mapped_column(Integer)
    captured: Mapped[int] = mapped_column(Integer)
    closed: Mapped[int] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime)


class Review(Base):
    """A week's review. The numbers are frozen when the week is closed."""

    __tablename__ = "reviews"

    week_start: Mapped[date] = mapped_column(primary_key=True)
    prepared_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    snapshot: Mapped[dict | None] = mapped_column(JSON)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
