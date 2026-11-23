"""Run due jobs in a background thread, catching up after sleep."""

import logging
import threading
from datetime import UTC, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.kernel import clock, db, jobs, settings

log = logging.getLogger(__name__)

TICK_SECONDS = 20

# (job kind, setting that holds its local time of day)
DAILY: list[tuple[str, str]] = [
    ("daily_backup", "backup_time"),
    ("morning_run", "morning_run_time"),
]


EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
# (job kind, minutes between runs)
INTERVALS: list[tuple[str, int]] = [("calendar_pull", 10)]


def latest_due(now: datetime, at: str, tz) -> datetime:
    """The most recent moment, at or before now, when a daily job at local time `at` was due."""
    local = now.astimezone(tz)
    due = datetime.combine(local.date(), time.fromisoformat(at), tz)
    if due > now:
        due -= timedelta(days=1)
    return due


def ensure_daily(session: Session, now: datetime) -> None:
    """Enqueue the latest occurrence of each daily and interval job. A long sleep yields one run."""
    tz = settings.tz(session)
    for kind, time_key in DAILY:
        due = latest_due(now, settings.get(session, time_key), tz)
        jobs.enqueue(session, kind, due, key=f"{kind}:{due.astimezone(tz).date()}")
    for kind, minutes in INTERVALS:
        step = timedelta(minutes=minutes)
        due = EPOCH + (now - EPOCH) // step * step
        jobs.enqueue(session, kind, due, key=f"{kind}:{due.isoformat()}")


def run_one(now: datetime) -> bool:
    """Claim and run one due job. Returns False when nothing is due."""
    with db.SessionLocal() as s:
        job = jobs.claim(s, now)
        s.commit()
    if job is None:
        return False
    with db.SessionLocal() as s:
        try:
            jobs.HANDLERS[job.kind](s, job.payload)
            jobs.finish(s, job.id, now)
            s.commit()
        except Exception as exc:
            log.exception("job %s %s failed", job.id, job.kind)
            s.rollback()
            jobs.retry_or_fail(s, job.id, now, repr(exc))
            s.commit()
    return True


def tick() -> int:
    """Enqueue recurring jobs, then run everything due. Returns the number of jobs run."""
    now = clock.now()
    with db.SessionLocal() as s:
        ensure_daily(s, now)
        s.commit()
    count = 0
    while run_one(now):
        count += 1
    return count


def startup() -> None:
    """Prepare the database for a new process."""
    with db.SessionLocal() as s:
        settings.seed(s)
        n = jobs.requeue_running(s)
        s.commit()
    if n:
        log.info("requeued %s half-finished jobs", n)


class Scheduler(threading.Thread):
    """Calls tick() every TICK_SECONDS until stopped."""

    def __init__(self):
        super().__init__(name="scheduler", daemon=True)
        self.stopped = threading.Event()

    def run(self) -> None:
        while not self.stopped.is_set():
            try:
                tick()
            except Exception:
                log.exception("scheduler tick failed")
            self.stopped.wait(TICK_SECONDS)

    def stop(self) -> None:
        self.stopped.set()
