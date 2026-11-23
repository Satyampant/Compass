"""Planning tables: one goal tree for all four horizons, and key results."""

from datetime import date, datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base, UTCDateTime

HORIZONS = ("year", "quarter", "month", "week")


class Goal(Base):
    """A year theme, quarter goal, month milestone or weekly outcome."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    horizon: Mapped[str] = mapped_column(String(8), index=True)
    title: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), index=True)
    period_start: Mapped[date] = mapped_column(index=True)
    period_end: Mapped[date]
    due_date: Mapped[date | None]
    short: Mapped[str | None] = mapped_column(String(24))
    color: Mapped[int | None] = mapped_column(Integer)
    done_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=1)


class KeyResult(Base):
    """A measurable result of a quarter goal: current against target."""

    __tablename__ = "key_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    target: Mapped[float] = mapped_column(Float)
    current: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(16), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
