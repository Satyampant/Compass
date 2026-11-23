from datetime import timedelta

from sqlalchemy import select

from app.kernel import clock
from app.modules.autopilot import cycle, fill
from app.modules.capture import service as capture
from app.modules.day.models import TimeBlock
from app.modules.learning import lifecycle
from app.modules.learning.models import LearningItem
from app.modules.planning import service as planning
from app.modules.planning.service import KeyResultIn
from tests.test_protect import meeting


def save(session, url, days_old=0, **extra):
    item = capture.capture(session, text=url, channel="web", key=url, **extra).item
    item.captured_at = clock.now() - timedelta(days=days_old)
    return item


def slots(session):
    return list(
        session.scalars(
            select(TimeBlock).where(TimeBlock.protected.is_(True)).order_by(TimeBlock.start)
        )
    )


def goal(session):
    year = planning.create_goal(session, "year", "Theme", clock.now().date())
    return planning.create_goal(
        session,
        "quarter",
        "Q",
        clock.now().date(),
        parent_id=year.id,
        key_results=[KeyResultIn("k", 1)],
    )


def test_started_item_is_booked_first_then_goal_linked_then_old(session, fake_clock, calendar):
    old = save(session, "https://old.com", days_old=18)
    linked = save(session, "https://goal.com", goal_id=goal(session).id)
    started = save(session, "https://started.com")
    lifecycle.transition(session, started, "book", booked_for=clock.now())
    lifecycle.transition(session, started, "start")
    cycle.run(session)
    held = [s.item_id for s in slots(session)[:3]]
    assert held == [started.id, linked.id, old.id]
    assert linked.state == old.state == "booked" and started.state == "learning"
    assert linked.booked_for == slots(session)[1].start
    first = slots(session)[1]
    assert (
        calendar.store[first.calendar_id][first.event_id]["summary"] == "Learning: https://goal.com"
    )


def test_items_too_long_for_the_slot_wait(session, fake_clock, calendar):
    long = save(session, "https://book.com")
    long.estimate_min = 120
    cycle.run(session)
    assert long.state == "inbox"


def test_booking_reserves_a_real_slot_and_unbooking_frees_it(client, session, fake_clock, calendar):
    cycle.run(session)
    item = save(session, "https://raft.github.io")
    session.commit()
    r = client.post(f"/v1/learning-items/{item.id}/transitions", json={"action": "book"}).json()
    monday = slots(session)[0]
    assert monday.item_id == item.id and r["booked_for"].startswith("2026-11-23T10:30")
    client.post(f"/v1/learning-items/{item.id}/transitions", json={"action": "unbook"})
    session.expire_all()
    assert slots(session)[0].item_id is None
    cycle.run(session)
    assert slots(session)[0].item_id is None  # pinned for your decision, not booked again


def test_booking_at_a_chosen_time_makes_a_block(client, session, fake_clock, calendar):
    item = save(session, "https://x.com")
    session.commit()
    when = "2026-11-24T06:00:00+00:00"
    client.post(
        f"/v1/learning-items/{item.id}/transitions", json={"action": "book", "booked_for": when}
    )
    block = session.scalars(select(TimeBlock).where(TimeBlock.item_id == item.id)).one()
    assert block.start.isoformat() == when and not block.protected
    client.post(f"/v1/learning-items/{item.id}/transitions", json={"action": "let_go"})
    session.expire_all()
    assert session.scalars(select(TimeBlock).where(TimeBlock.item_id == item.id)).all() == []


def test_one_tap_swaps_the_item(client, session, fake_clock, calendar):
    a = save(session, "https://a.com", days_old=10)
    b = save(session, "https://b.com", days_old=5)
    cycle.run(session)
    monday = slots(session)[0]
    assert monday.item_id == a.id
    for s in slots(session)[1:]:
        fill.detach(session, s)
    lifecycle.transition(session, b, "unbook")
    b.pinned_at = None
    session.commit()
    r = client.post(f"/v1/blocks/{monday.id}/swap").json()
    session.expire_all()
    assert r["item_id"] == b.id and session.get(LearningItem, a.id).state == "inbox"


def test_slot_lost_to_a_meeting_returns_its_item_to_the_list(session, fake_clock, calendar):
    item = save(session, "https://a.com")
    cycle.run(session)
    assert slots(session)[0].item_id == item.id
    calendar.put("primary", meeting("Offsite", 23, "15:00", "20:00"))
    cycle.run(session)
    assert slots(session)[0].status == "not_kept" and slots(session)[0].item_id is None
    assert item.state == "inbox" and item.pinned_at is not None
    assert all(s.item_id != item.id for s in slots(session))


def test_moving_a_slot_moves_its_item(session, fake_clock, calendar):
    item = save(session, "https://a.com")
    cycle.run(session)
    calendar.put("primary", meeting("Call", 23, "16:00", "16:30"))
    cycle.run(session)
    assert item.booked_for == slots(session)[0].start == clock.now().replace(hour=11, minute=0)
