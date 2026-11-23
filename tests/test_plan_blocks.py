from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.modules.autopilot import cycle
from app.modules.day.models import TimeBlock
from tests.test_protect import meeting

IST = timedelta(hours=5, minutes=30)


def ist(day, h, m=0):
    return datetime(2026, 11, day, h, m, tzinfo=UTC) - IST


def task(client, title, minutes):
    return client.post(
        "/v1/tasks", json={"title": title, "estimate_min": minutes, "planned_date": "2026-11-24"}
    ).json()["id"]


def test_proposal_goes_around_meetings_and_the_learning_slot(client, session, fake_clock, calendar):
    calendar.put("primary", meeting("Standup", 24, "08:00", "09:00"))
    calendar.put("primary", meeting("Investor call", 24, "13:00", "14:00"))
    cycle.run(session)
    session.commit()
    deep = task(client, "Split parity", 180)
    call = task(client, "Cap table", 60)
    review = task(client, "License review", 90)
    huge = task(client, "Rewrite engine", 600)
    r = client.post("/v1/days/2026-11-24/propose", json={"task_ids": [deep, call, review, huge]})
    got = {p["task_id"]: (p["start"], p["end"]) for p in r.json()}
    starts = {k: datetime.fromisoformat(v[0]) for k, v in got.items()}
    assert starts[deep] == ist(24, 9)  # longest morning gap: 09:00 to 13:00
    assert starts[call] == ist(24, 12)  # earliest gap left that fits
    assert starts[review] == ist(24, 14)  # after the call
    assert huge not in got  # no room


def test_confirmed_plan_is_written_to_the_calendar(client, session, fake_clock, calendar):
    cycle.run(session)
    session.commit()
    a = task(client, "Split parity", 120)
    blocks = client.post("/v1/days/2026-11-24/propose", json={"task_ids": [a]}).json()
    r = client.post("/v1/days/2026-11-24/plan", json={"top": [a], "blocks": blocks})
    assert r.status_code == 200
    cycle.run(session)
    session.commit()
    block = session.scalars(select(TimeBlock).where(TimeBlock.task_id == a)).one()
    event = calendar.store[block.calendar_id][block.event_id]
    assert event["summary"] == "Split parity"
    assert datetime.fromisoformat(event["start"]["dateTime"]) == ist(24, 8)

    # Planning again replaces the day's task blocks instead of adding to them.
    moved = [{**blocks[0], "start": ist(24, 10).isoformat(), "end": ist(24, 12).isoformat()}]
    client.post("/v1/days/2026-11-24/plan", json={"top": [a], "blocks": moved})
    session.expire_all()
    cycle.run(session)
    session.commit()
    rows = session.scalars(select(TimeBlock).where(TimeBlock.task_id == a)).all()
    assert [r.start for r in rows] == [ist(24, 10)]
    draft = client.get("/v1/days/2026-11-24/plan").json()
    assert [b["title"] for b in draft["blocks"]] == ["Split parity"]
