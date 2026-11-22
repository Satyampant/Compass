"""The notifications table: every nudge, sent or held back by the budget."""

from datetime import date, datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base, UTCDateTime


class Notification(Base):
    """A nudge for a local date."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(32))
    item_id: Mapped[int | None]
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    message_id: Mapped[int | None] = mapped_column(Integer)
