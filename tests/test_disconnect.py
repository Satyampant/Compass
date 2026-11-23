from sqlalchemy import select

from app.modules.autopilot import cycle
from app.modules.day.models import TimeBlock
from tests.test_fill import save, slots
from tests.test_protect import meeting


def test_without_a_token_every_other_screen_works(client, session, fake_clock):
    cycle.run(session)
    session.commit()
    status = client.get("/v1/calendar").json()
    assert status["connected"] is False and "not signed in" in status["error"]
    t = client.post("/v1/tasks", json={"title": "Split parity"}).json()
    item = client.post("/v1/captures", json={"text": "https://raft.github.io"}).json()["item_id"]
    r = client.post(f"/v1/learning-items/{item}/transitions", json={"action": "book"})
    assert r.status_code == 200
    for path in (
        "/v1/today",
        "/v1/week",
        "/v1/learning-items",
        "/v1/goals?horizon=year",
        "/v1/days/2026-11-24/plan",
    ):
        assert client.get(path).status_code == 200, path
    plan = {"decisions": [{"task_id": t["id"], "action": "tomorrow"}], "top": [t["id"]]}
    assert client.post("/v1/days/2026-11-24/plan", json=plan).status_code == 200
    assert client.post("/v1/calendar/resync").json()["connected"] is False


def test_resync_rebuilds_meetings_and_rewrites_deleted_blocks(
    client, session, fake_clock, calendar
):
    save(session, "https://a.com")
    calendar.put("primary", meeting("Call", 24, "10:00", "11:00"))
    cycle.run(session)
    session.commit()
    monday = slots(session)[0]
    calendar.cancel(monday.calendar_id, monday.event_id)  # deleted by hand in Google
    old = monday.event_id
    status = client.post("/v1/calendar/resync").json()
    session.expire_all()
    assert status["connected"] is True
    monday = slots(session)[0]
    assert monday.event_id != old and calendar.store[monday.calendar_id][monday.event_id]["summary"]
    meetings = session.scalars(select(TimeBlock).where(TimeBlock.source == "calendar")).all()
    assert [m.title for m in meetings] == ["Call"]
