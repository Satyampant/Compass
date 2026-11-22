"""Accept captures from any channel and turn them into items, tasks or notes."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, events, jobs, settings
from app.modules.capture import links
from app.modules.capture.models import Capture, Note
from app.modules.day.models import Task
from app.modules.day.service import create_task
from app.modules.learning import lifecycle
from app.modules.learning.models import OPEN_STATES, LearningItem

KINDS = ("learn", "task", "note")


@dataclass
class CaptureResult:
    """What happened to a capture. outcome is item, duplicate, pending, task or note."""

    capture: Capture
    outcome: str
    item: LearningItem | None = None
    task: Task | None = None
    note: Note | None = None


def capture(
    session: Session,
    *,
    text: str,
    channel: str,
    key: str,
    at: datetime | None = None,
    kind: str | None = None,
) -> CaptureResult:
    """Store a capture once per key. A link becomes an item; plain text waits for a kind."""
    existing = session.scalars(select(Capture).where(Capture.idempotency_key == key)).first()
    if existing:
        return result_of(session, existing)
    at = at or clock.now()
    url, rest = links.extract(text)
    cap = Capture(idempotency_key=key, channel=channel, text=text, url=url, created_at=at)
    session.add(cap)
    session.flush()
    events.record(session, "capture.created", "capture", cap.id, channel=channel)
    if url:
        return _from_link(session, cap, url, rest, at)
    if kind:
        return resolve(session, cap, kind)
    return CaptureResult(cap, "pending")


def _from_link(session: Session, cap: Capture, url: str, rest: str, at: datetime):
    digest = links.url_hash(url)
    open_item = session.scalars(
        select(LearningItem).where(
            LearningItem.url_hash == digest, LearningItem.state.in_(OPEN_STATES)
        )
    ).first()
    if open_item:
        if open_item.state == "inbox":
            lifecycle.pin_to_desk(open_item, clock.now(), settings.today(session))
        cap.status, cap.item_id = "duplicate", open_item.id
        events.record(session, "capture.duplicate", "learning_item", open_item.id)
        return CaptureResult(cap, "duplicate", item=open_item)
    item = lifecycle.create(
        session,
        title=rest or url,
        captured_at=at,
        url=url,
        url_hash=digest,
        source_type=links.source_type(url),
    )
    cap.status, cap.item_id = "item", item.id
    jobs.enqueue(session, "enrich_item", clock.now(), item_id=item.id)
    return CaptureResult(cap, "item", item=item)


def resolve(session: Session, cap: Capture, kind: str) -> CaptureResult:
    """Turn a pending plain-text capture into an item, a task or a note."""
    if cap.status != "pending":
        return result_of(session, cap)
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    body = cap.text.strip()
    if kind == "learn":
        item = lifecycle.create(session, title=body, captured_at=cap.created_at, source_type="note")
        cap.status, cap.item_id = "item", item.id
        return CaptureResult(cap, "item", item=item)
    if kind == "task":
        task = create_task(session, body, settings.today(session))
        cap.status, cap.task_id = "task", task.id
        return CaptureResult(cap, "task", task=task)
    note = Note(body=body, created_at=cap.created_at)
    session.add(note)
    session.flush()
    events.record(session, "note.created", "note", note.id)
    cap.status, cap.note_id = "note", note.id
    return CaptureResult(cap, "note", note=note)


def result_of(session: Session, cap: Capture) -> CaptureResult:
    """Rebuild the result of a capture already stored."""
    return CaptureResult(
        cap,
        cap.status,
        item=session.get(LearningItem, cap.item_id) if cap.item_id else None,
        task=session.get(Task, cap.task_id) if cap.task_id else None,
        note=session.get(Note, cap.note_id) if cap.note_id else None,
    )
