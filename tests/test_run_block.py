from datetime import timedelta

from sqlalchemy import select

from app.kernel import clock
from app.kernel.models import Event
from app.modules.autopilot import booking, cycle
from app.modules.capture import service as capture
from app.modules.day.models import TimeBlock
from app.modules.learning.models import LearningItem
from tests.test_fill import slots


def save(session, url, minutes=90):
    item = capture.capture(session, text=url, channel="web", key=url).item
    item.estimate_min = minutes
    return item


def at_block(fake_clock, block, minutes=0):
    fake_clock.set(block.start + timedelta(minutes=minutes))


def test_unfinished_item_resumes_in_the_next_block_with_progress(session, fake_clock, calendar):
    item = save(session, "https://ddia.example.com", minutes=40)
    cycle.run(session)
    monday, wednesday = slots(session)[:2]
    assert monday.item_id == item.id
    at_block(fake_clock, monday, 5)
    booking.move(session, item, "start")
    assert monday.status == "started"
    fake_clock.set(monday.end + timedelta(minutes=1))
    cycle.run(session)
    assert monday.status == "kept"
    assert item.state == "booked" and item.progress_min == 40
    assert wednesday.item_id == item.id and item.booked_for == wednesday.start
    at_block(fake_clock, wednesday)
    booking.move(session, item, "start")
    fake_clock.set(wednesday.end + timedelta(minutes=1))
    cycle.run(session)
    assert monday.status == "kept" and item.progress_min == 85
    assert len([s for s in slots(session) if s.item_id == item.id]) == 3


def test_missed_block_returns_the_item_to_the_top_of_the_list(session, fake_clock, calendar):
    item = save(session, "https://raft.github.io", minutes=30)
    cycle.run(session)
    monday = slots(session)[0]
    fake_clock.set(monday.end + timedelta(minutes=5))
    cycle.run(session)
    assert monday.status == "missed"
    assert item.state == "inbox" and item.pinned_at is not None
    assert item.shown_on == clock.now().date()
    missed = session.scalars(select(Event).where(Event.kind == "block.missed")).all()
    assert [e.entity_id for e in missed] == [monday.id]
    cycle.run(session)
    assert item.state == "inbox"  # pinned for your decision, not booked again


def test_save_progress(client, session, fake_clock, calendar):
    item = save(session, "https://x.com", minutes=40)
    cycle.run(session)
    at_block(fake_clock, slots(session)[0])
    booking.move(session, item, "start")
    session.commit()
    r = client.post(f"/v1/learning-items/{item.id}/progress", json={"minutes": 25}).json()
    assert r["progress_min"] == 25
    other = save(session, "https://y.com")
    session.commit()
    assert (
        client.post(f"/v1/learning-items/{other.id}/progress", json={"minutes": 5}).status_code
        == 409
    )


def test_finished_in_its_block_is_simply_kept(session, fake_clock, calendar):
    item = save(session, "https://z.com", minutes=30)
    cycle.run(session)
    monday = slots(session)[0]
    at_block(fake_clock, monday)
    booking.move(session, item, "start")
    booking.move(session, item, "finish", note="Notes saved")
    fake_clock.set(monday.end + timedelta(minutes=1))
    cycle.run(session)
    assert monday.status == "kept" and session.get(LearningItem, item.id).state == "learned"
    assert session.scalars(select(TimeBlock).where(TimeBlock.status == "missed")).all() == []
