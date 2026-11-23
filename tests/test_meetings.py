from datetime import UTC, datetime

from sqlalchemy import select

from app.kernel import settings
from app.modules.day import meetings
from app.modules.day.models import TimeBlock


def event(id, start, end, **extra):
    return {
        "id": id,
        "summary": f"Meeting {id}",
        "status": "confirmed",
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        **extra,
    }


def blocks(session):
    return {b.event_id: b for b in session.scalars(select(TimeBlock))}


def test_meeting_added_then_moved_then_deleted(session, fake_clock, calendar):
    calendar.put("primary", event("a", "2026-11-23T13:00:00+05:30", "2026-11-23T14:00:00+05:30"))
    meetings.pull(session)
    b = blocks(session)["a"]
    assert (b.kind, b.source, b.title) == ("meeting", "calendar", "Meeting a")
    assert b.start == datetime(2026, 11, 23, 7, 30, tzinfo=UTC)
    calendar.put("primary", event("a", "2026-11-23T15:00:00+05:30", "2026-11-23T16:00:00+05:30"))
    meetings.pull(session)
    assert blocks(session)["a"].start == datetime(2026, 11, 23, 9, 30, tzinfo=UTC)
    calendar.cancel("primary", "a")
    meetings.pull(session)
    assert blocks(session) == {}
    assert settings.get(session, meetings.STATUS_KEY)["connected"]


def test_all_day_and_declined_are_skipped(session, fake_clock, calendar):
    calendar.put(
        "primary",
        {
            "id": "hol",
            "status": "confirmed",
            "start": {"date": "2026-11-24"},
            "end": {"date": "2026-11-25"},
        },
    )
    calendar.put(
        "primary",
        event(
            "no",
            "2026-11-23T10:00:00+05:30",
            "2026-11-23T11:00:00+05:30",
            attendees=[{"self": True, "responseStatus": "declined"}],
        ),
    )
    meetings.pull(session)
    assert blocks(session) == {}


def test_expired_cursor_triggers_full_resync(session, fake_clock, calendar):
    calendar.put("primary", event("a", "2026-11-23T13:00:00+05:30", "2026-11-23T14:00:00+05:30"))
    meetings.pull(session)
    cursor = settings.get(session, meetings.cursor_key("primary"))
    calendar.expired.add(cursor)
    calendar.put("primary", event("b", "2026-11-23T15:00:00+05:30", "2026-11-23T16:00:00+05:30"))
    meetings.pull(session)
    assert set(blocks(session)) == {"a", "b"}


def test_not_signed_in_is_recorded_not_raised(session, fake_clock):
    meetings.pull(session)
    status = settings.get(session, meetings.STATUS_KEY)
    assert status["connected"] is False and "not signed in" in status["error"]


def test_pull_job_runs_every_ten_minutes(session, fake_clock, calendar):
    from app.kernel import scheduler

    calendar.put("primary", event("a", "2026-11-23T13:00:00+05:30", "2026-11-23T14:00:00+05:30"))
    scheduler.tick()
    assert "a" in blocks(session)
    calendar.put("primary", event("b", "2026-11-23T15:00:00+05:30", "2026-11-23T16:00:00+05:30"))
    scheduler.tick()
    session.expire_all()
    assert "b" not in blocks(session)
    fake_clock.advance(minutes=10)
    scheduler.tick()
    session.expire_all()
    assert "b" in blocks(session)


def test_calendar_list(client, calendar):
    assert client.get("/v1/calendar/calendars").json() == ["primary"]


def test_calendar_list_when_signed_out(client):
    assert client.get("/v1/calendar/calendars").json() == []
