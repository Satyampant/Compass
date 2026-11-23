"""The status page: did everything run? Each row turns to a warning when it is older than
expected. A Mac asleep for a day shows warnings too, which is the truth."""

from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.kernel import backup, clock, settings
from app.kernel.models import Job
from app.modules.day import meetings
from app.modules.notify import bot

# (row name, job kind, how old the last run may be)
JOB_ROWS = [
    ("Morning run", "morning_run", timedelta(hours=26)),
    ("Morning brief", "morning_brief", timedelta(hours=26)),
    ("Day rollup", "day_rollup", timedelta(hours=26)),
    ("Shutdown nudge", "shutdown_nudge", timedelta(hours=26)),
    ("Weekly review", "review_prepare", timedelta(days=8)),
    ("Calendar sync", "calendar_pull", timedelta(minutes=30)),
]
TELEGRAM_MAX_AGE = timedelta(minutes=5)


class Row(BaseModel):
    name: str
    last: datetime | None
    ok: bool
    detail: str


class Failure(BaseModel):
    kind: str
    finished_at: datetime | None
    attempts: int
    error: str | None


class Status(BaseModel):
    rows: list[Row]
    failures: list[Failure]


def row(name: str, last: datetime | None, max_age: timedelta, detail: str = "") -> Row:
    fresh = last is not None and clock.now() - last <= max_age
    detail = detail or ("never ran" if last is None else "")
    return Row(name=name, last=last, ok=fresh, detail=detail)


def last_done(session: Session, kind: str) -> datetime | None:
    return session.scalar(
        select(func.max(Job.finished_at)).where(Job.kind == kind, Job.status == "done")
    )


def backup_row(session: Session) -> Row:
    """Fresh when the newest copy is from today or yesterday, judged by the date in its name."""
    copies = sorted(backup.backup_dir(session).glob(f"{backup.PREFIX}*.db"))
    if not copies:
        return Row(name="Backup", last=None, ok=False, detail="no backup yet")
    newest = copies[-1]
    made = date.fromisoformat(newest.stem.removeprefix(backup.PREFIX))
    return Row(
        name="Backup",
        last=datetime.fromtimestamp(newest.stat().st_mtime, UTC),
        ok=made >= settings.today(session) - timedelta(days=1),
        detail=f"{newest.name}, {len(copies)} kept",
    )


def status(session: Session) -> Status:
    rows = [row(name, last_done(session, kind), age) for name, kind, age in JOB_ROWS]
    cal = settings.get(session, meetings.STATUS_KEY) or {}
    if not cal.get("connected"):
        rows[-1].ok, rows[-1].detail = False, cal.get("error") or "not connected"
    polled = settings.get(session, bot.LAST_POLL_KEY)
    rows.append(row("Telegram check", polled and datetime.fromisoformat(polled), TELEGRAM_MAX_AGE))
    rows.append(backup_row(session))
    failed = session.scalars(
        select(Job).where(Job.status == "failed").order_by(Job.finished_at.desc()).limit(10)
    )
    return Status(
        rows=rows,
        failures=[
            Failure(kind=j.kind, finished_at=j.finished_at, attempts=j.attempts, error=j.last_error)
            for j in failed
        ],
    )
