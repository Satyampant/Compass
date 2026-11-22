"""The jobs table: enqueue, claim, finish, retry."""

from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.kernel.models import Job

MAX_ATTEMPTS = 5

Handler = Callable[[Session, dict], None]
HANDLERS: dict[str, Handler] = {}


def handler(kind: str) -> Callable[[Handler], Handler]:
    """Register the function that runs jobs of this kind."""

    def wrap(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn

    return wrap


def enqueue(
    session: Session, kind: str, run_at: datetime, key: str | None = None, **payload
) -> None:
    """Add a job. A job whose key already exists is not added again."""
    stmt = insert(Job).values(
        kind=kind, key=key, payload=payload, run_at=run_at, status="queued", attempts=0
    )
    session.execute(stmt.on_conflict_do_nothing(index_elements=["key"]))


def claim(session: Session, now: datetime) -> Job | None:
    """Mark the oldest due job as running and return it."""
    oldest = (
        select(Job.id)
        .where(Job.status == "queued", Job.run_at <= now)
        .order_by(Job.run_at, Job.id)
        .limit(1)
        .scalar_subquery()
    )
    stmt = (
        update(Job)
        .where(Job.id == oldest)
        .values(status="running", started_at=now, attempts=Job.attempts + 1)
        .returning(Job)
    )
    return session.scalars(stmt).one_or_none()


def finish(session: Session, job_id: int, now: datetime) -> None:
    """Mark a job done."""
    job = session.get(Job, job_id)
    job.status, job.finished_at = "done", now


def retry_or_fail(session: Session, job_id: int, now: datetime, error: str) -> None:
    """Queue a failed job again with backoff, or give up after MAX_ATTEMPTS."""
    job = session.get(Job, job_id)
    job.last_error = error
    if job.attempts >= MAX_ATTEMPTS:
        job.status, job.finished_at = "failed", now
    else:
        job.status, job.run_at = "queued", now + timedelta(minutes=2**job.attempts)


def requeue_running(session: Session) -> int:
    """Put back anything a crash or a closed lid left half done."""
    result = session.execute(update(Job).where(Job.status == "running").values(status="queued"))
    return result.rowcount
