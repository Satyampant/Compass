from datetime import UTC, datetime

from app.modules.day import blocks, meetings


def meeting(id, start, end):
    return {
        "id": id,
        "summary": id,
        "status": "confirmed",
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }


def test_today_lists_meetings_and_blocks_in_the_window(client, session, fake_clock, calendar):
    calendar.put(
        "primary",
        meeting("Investor call", "2026-11-23T13:00:00+05:30", "2026-11-23T14:00:00+05:30"),
    )
    calendar.put(
        "primary", meeting("Late dinner", "2026-11-23T21:00:00+05:30", "2026-11-23T22:00:00+05:30")
    )
    calendar.put(
        "primary", meeting("Tomorrow", "2026-11-24T10:00:00+05:30", "2026-11-24T11:00:00+05:30")
    )
    meetings.pull(session)
    blocks.create(
        session,
        "learning",
        datetime(2026, 11, 23, 10, 30, tzinfo=UTC),
        datetime(2026, 11, 23, 11, 15, tzinfo=UTC),
        "Learning block",
        protected=True,
    )
    session.commit()
    today = client.get("/v1/today").json()
    assert [(b["title"], b["source"]) for b in today["blocks"]] == [
        ("Investor call", "calendar"),
        ("Learning block", "compass"),
    ]
    assert [(m["label"], m["at"]) for m in today["marks"]] == [
        ("NSE opens", "2026-11-23T09:15:00+05:30"),
        ("NSE closes", "2026-11-23T15:30:00+05:30"),
    ]


def test_no_market_marks_at_the_weekend(client, fake_clock):
    fake_clock.set(datetime(2026, 11, 28, 3, 0, tzinfo=UTC))
    assert client.get("/v1/today").json()["marks"] == []
