"""PRD 'accepted when' checks for phase 2, in the PRD's words.

Checks that need real Google, the phone or a week of use are in docs/acceptance-p2.md.
"""

from datetime import timedelta

from sqlalchemy import select

from app.kernel import scheduler
from app.modules.autopilot import cycle
from app.modules.capture import service as capture
from app.modules.day import blocks
from app.modules.day.models import TimeBlock
from tests.test_protect import ist, meeting


def items(session, n):
    for i in range(n):
        capture.capture(session, text=f"https://site{i}.example.com", channel="web", key=str(i))
    session.commit()


def test_sunday_evening_next_weeks_four_blocks_have_an_item_each(session, fake_clock, calendar):
    items(session, 12)
    fake_clock.set(ist(29, "19:00"))
    cycle.run(session)
    nxt = session.scalars(
        select(TimeBlock)
        .where(TimeBlock.protected.is_(True), TimeBlock.start >= ist(30, "00:00"))
        .order_by(TimeBlock.start)
    ).all()
    assert len(nxt) == 4 and all(b.item_id for b in nxt)
    cal = session.scalar(select(TimeBlock.calendar_id).where(TimeBlock.id == nxt[0].id))
    assert all(calendar.store[cal][b.event_id]["summary"].startswith("Learning: ") for b in nxt)


def test_a_meeting_added_in_google_shows_in_today_within_ten_minutes(
    client, session, fake_clock, calendar
):
    scheduler.tick()
    calendar.put("primary", meeting("Investor call", 23, "13:00", "14:00"))
    fake_clock.advance(minutes=10)
    scheduler.tick()
    titles = [b["title"] for b in client.get("/v1/today").json()["blocks"]]
    assert "Investor call" in titles


def test_hiding_the_compass_calendar_hides_every_compass_block_and_nothing_else(
    client, session, fake_clock, calendar
):
    items(session, 3)
    calendar.put("primary", meeting("Standup", 24, "09:00", "09:30"))
    cycle.run(session)
    session.commit()
    t = client.post("/v1/tasks", json={"title": "Deep work", "planned_date": "2026-11-24"}).json()
    placed = client.post("/v1/days/2026-11-24/propose", json={"task_ids": [t["id"]]}).json()
    client.post("/v1/days/2026-11-24/plan", json={"top": [t["id"]], "blocks": placed})
    session.expire_all()
    cycle.run(session)
    session.commit()
    compass_id = session.scalar(
        select(TimeBlock.calendar_id).where(TimeBlock.source == "compass").limit(1)
    )
    ours = session.scalars(select(TimeBlock).where(TimeBlock.source == "compass")).all()
    assert ours and {b.calendar_id for b in ours} == {compass_id}
    assert {b.event_id for b in ours} == {
        e["id"] for e in calendar.store[compass_id].values() if e.get("status") != "cancelled"
    }
    assert not any(blocks.marked(e) for e in calendar.store["primary"].values())
    assert all(w[1] == compass_id for w in calendar.writes if w[0] != "create_calendar")


def test_a_block_that_passes_without_a_start_counts_as_not_kept(session, fake_clock, calendar):
    items(session, 1)
    cycle.run(session)
    slot = session.scalars(
        select(TimeBlock).where(TimeBlock.protected.is_(True)).order_by(TimeBlock.start)
    ).first()
    fake_clock.set(slot.end + timedelta(minutes=1))
    cycle.run(session)
    assert slot.status == "missed"
