import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.modules.day import blocks, meetings
from app.modules.day.models import TimeBlock

START = datetime(2026, 11, 23, 10, 30, tzinfo=UTC)
END = datetime(2026, 11, 23, 11, 15, tzinfo=UTC)
MEETING = {
    "id": "m1",
    "summary": "Investor call",
    "status": "confirmed",
    "start": {"dateTime": "2026-11-23T13:00:00+05:30"},
    "end": {"dateTime": "2026-11-23T14:00:00+05:30"},
}


def test_block_is_written_to_the_compass_calendar(session, fake_clock, calendar):
    block = blocks.create(session, "learning", START, END, "Learning block", protected=True)
    blocks.push(session)
    assert calendar.writes[0] == ("create_calendar", "Compass")
    cal_id = block.calendar_id
    event = calendar.store[cal_id][block.event_id]
    assert blocks.marked(event) and event["summary"] == "Learning block"
    blocks.change(session, block, title="K8s Services", start=START.replace(hour=11))
    blocks.push(session)
    assert calendar.store[cal_id][block.event_id]["summary"] == "K8s Services"
    blocks.remove(session, block)
    blocks.push(session)
    assert calendar.store[cal_id][block.event_id]["status"] == "cancelled"
    assert session.scalars(select(TimeBlock)).all() == []


def test_blocks_wait_while_signed_out_then_push(session, fake_clock, monkeypatch):
    block = blocks.create(session, "task", START, END, "Deep work")
    blocks.push(session)
    assert block.sync == "push" and block.event_id is None
    from app.modules.integrations import gcal
    from tests.fakes import FakeCalendar

    fake = FakeCalendar()
    monkeypatch.setattr(gcal, "connect", lambda: fake)
    blocks.push(session)
    assert block.sync == "synced" and block.event_id


def test_no_code_path_changes_an_event_without_the_marker(session, fake_clock, calendar):
    calendar.put("primary", dict(MEETING))
    meetings.pull(session)
    meeting = session.scalars(select(TimeBlock)).one()
    with pytest.raises(blocks.ReadOnly):
        blocks.change(session, meeting, title="x")
    with pytest.raises(blocks.ReadOnly):
        blocks.remove(session, meeting)
    with pytest.raises(blocks.ReadOnly):
        blocks.push_one(session, calendar, "primary", meeting)

    # A Compass block whose event lost its marker is left alone.
    block = blocks.create(session, "task", START, END, "Deep work")
    blocks.push(session)
    event = calendar.store[block.calendar_id][block.event_id]
    event["extendedProperties"] = {}
    blocks.change(session, block, title="Renamed")
    blocks.remove(session, block)
    writes = len(calendar.writes)
    blocks.push(session)
    assert len(calendar.writes) == writes and block.sync == "conflict"
    assert calendar.store["primary"]["m1"] == MEETING
    assert all(w[1] in calendar.owned for w in calendar.writes if w[0] != "create_calendar")


def test_only_blocks_module_calls_calendar_writes():
    root = Path(__file__).resolve().parents[1] / "app"
    callers = {
        str(p.relative_to(root))
        for p in root.rglob("*.py")
        if re.search(r"\.(insert_event|patch_event|delete_event|create_calendar)\(", p.read_text())
    }
    assert callers == {"modules/day/blocks.py"}


def test_compass_events_are_never_read_as_meetings(session, fake_clock, calendar):
    calendar.put(
        "primary", {**MEETING, "id": "m2", "extendedProperties": {"private": {"compass": "1"}}}
    )
    meetings.pull(session)
    assert session.scalars(select(TimeBlock)).all() == []
