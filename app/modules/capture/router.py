"""HTTP API for captures from the web app and the extension."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.kernel.db import SessionDep
from app.modules.capture import service
from app.modules.capture.models import Capture
from app.modules.planning.tags import check_goal

router = APIRouter(prefix="/v1/captures", tags=["capture"])


class CaptureIn(BaseModel):
    text: str
    kind: str | None = None
    channel: str = "web"
    goal_id: int | None = None
    reason: str | None = None


class ResolveIn(BaseModel):
    kind: str


class CaptureOut(BaseModel):
    capture_id: int
    outcome: str
    item_id: int | None = None
    task_id: int | None = None
    note_id: int | None = None
    title: str | None = None
    first_saved_at: str | None = None


def out(result: service.CaptureResult) -> CaptureOut:
    """Serialise a capture result."""
    thing = result.item or result.task or result.note
    return CaptureOut(
        capture_id=result.capture.id,
        outcome=result.outcome,
        item_id=result.item.id if result.item else None,
        task_id=result.task.id if result.task else None,
        note_id=result.note.id if result.note else None,
        title=getattr(thing, "title", None) or getattr(thing, "body", None),
        first_saved_at=result.item.captured_at.isoformat() if result.item else None,
    )


@router.post("", status_code=202)
def create_capture(
    body: CaptureIn,
    session: SessionDep,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> CaptureOut:
    if not body.text.strip():
        raise HTTPException(422, "nothing to capture")
    if body.kind and body.kind not in service.KINDS:
        raise HTTPException(422, f"kind must be one of {service.KINDS}")
    check_goal(session, body.goal_id)
    result = service.capture(
        session,
        text=body.text,
        channel=body.channel,
        key=idempotency_key or str(uuid.uuid4()),
        kind=body.kind,
        goal_id=body.goal_id,
        reason=(body.reason or "").strip() or None,
    )
    session.commit()
    return out(result)


@router.post("/{capture_id}/resolve")
def resolve_capture(capture_id: int, body: ResolveIn, session: SessionDep) -> CaptureOut:
    cap = session.get(Capture, capture_id)
    if cap is None:
        raise HTTPException(404, "capture not found")
    if body.kind not in service.KINDS:
        raise HTTPException(422, f"kind must be one of {service.KINDS}")
    result = service.resolve(session, cap, body.kind)
    session.commit()
    return out(result)
