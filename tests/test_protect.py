from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.kernel import clock
from app.modules.autopilot import cycle, protect
from app.modules.day.models import TimeBlock

IST = timedelta(hours=5, minutes=30)


def ist(day, hm):
    h, m = map(int, hm.split(":"))
    return datetime(2026, 11, day, h, m, tzinfo=UTC) - IST


def slots(session):
    return list(
        session.scalars(
            select(TimeBlock).where(TimeBlock.protected.is_(True)).order_by(TimeBlock.slot_at)
        )
    )


def meeting(id, day, start, end):
    at = lambda hm: {"dateTime": f"2026-11-{day:02d}T{hm}:00+05:30"}  # noqa: E731
    return {"id": id, "summary": id, "status": "confirmed", "start": at(start), "end": at(end)}


def test_sunday_evening_next_weeks_four_slots_exist(session, fake_clock, calendar):
    fake_clock.set(ist(29, "19:00"))  # Sunday evening
    cycle.run(session)
    nxt = [s for s in slots(session) if s.slot_at >= ist(30, "00:00")]
    assert [s.start.astimezone(UTC) for s in nxt] == [
        ist(30, "16:00"),
        ist(30, "16:00") + timedelta(days=2),
        ist(30, "16:00") + timedelta(days=4),
        ist(30, "10:00") + timedelta(days=5),
    ]
    assert all(s.event_id for s in nxt)  # written to the Compass calendar
    cycle.run(session)
    assert len(slots(session)) == len(nxt)  # idempotent


def test_slots_already_past_are_not_made(session, fake_clock):
    fake_clock.set(ist(25, "17:00"))  # Wednesday after its slot
    protect.run(session)
    this_week = [s for s in slots(session) if s.slot_at < ist(30, "00:00")]
    assert [s.slot_at for s in this_week] == [ist(27, "16:00"), ist(28, "10:00")]


def test_clashing_meeting_moves_the_slot(session, fake_clock, calendar):
    calendar.put("primary", meeting("Investor call", 23, "15:30", "16:30"))
    cycle.run(session)
    monday = slots(session)[0]
    assert monday.start == ist(23, "16:30") and monday.end == ist(23, "17:15")
    assert monday.status == "planned"


def test_full_day_marks_the_slot_not_kept(session, fake_clock, calendar):
    calendar.put("primary", meeting("Offsite", 23, "15:00", "20:00"))
    cycle.run(session)
    monday = slots(session)[0]
    assert monday.status == "not_kept" and monday.start == ist(23, "16:00")
    calendar.cancel("primary", "Offsite")
    cycle.run(session)
    assert slots(session)[0].status == "planned"


def test_moved_slot_is_written_to_the_calendar(session, fake_clock, calendar):
    cycle.run(session)
    monday = slots(session)[0]
    calendar.put("primary", meeting("Call", 23, "16:00", "16:30"))
    cycle.run(session)
    event = calendar.store[monday.calendar_id][monday.event_id]
    assert event["start"]["dateTime"].startswith(str(ist(23, "16:30").date()))
    assert datetime.fromisoformat(event["start"]["dateTime"]) == ist(23, "16:30")
    assert clock.now() < monday.start
