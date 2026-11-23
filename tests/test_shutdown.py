from datetime import date

from app.modules.day.models import DailyLog


def test_shutdown_closes_the_day_with_its_line(client, session, fake_clock):
    today = client.get("/v1/today").json()
    assert today["closed_at"] is None and not today["tomorrow_planned"]
    r = client.post("/v1/days/2026-11-23/shutdown", json={"learned_line": " Raft needs a quorum "})
    assert r.status_code == 200 and r.json()["learned_line"] == "Raft needs a quorum"
    log = session.get(DailyLog, date(2026, 11, 23))
    assert log.closed_at is not None
    today = client.get("/v1/today").json()
    assert today["closed_at"] and today["learned_line"] == "Raft needs a quorum"


def test_shutdown_needs_a_line(client, fake_clock):
    assert client.post("/v1/days/2026-11-23/shutdown", json={"learned_line": ""}).status_code == 422


def test_planning_tomorrow_shows_on_today(client, fake_clock):
    client.post("/v1/days/2026-11-24/plan", json={})
    assert client.get("/v1/today").json()["tomorrow_planned"]
