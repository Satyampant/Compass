import pytest

from app.kernel import db, migrate
from app.modules.autopilot import cycle
from app.modules.system import export
from tests.test_fill import save
from tests.test_goal_links import tree
from tests.test_protect import meeting

PATHS = [
    "/v1/today",
    "/v1/week",
    "/v1/learning-items?state=inbox,booked,learning,learned,let_go,expired",
    "/v1/goals?horizon=year",
    "/v1/goals?horizon=quarter",
    "/v1/goals?horizon=week",
    "/v1/reviews/2026-11-16",
    "/v1/days/2026-11-24/plan",
]


def test_export_loads_into_an_empty_database_and_shows_the_same(
    client, session, fake_clock, calendar, tmp_path
):
    year, quarter, week = tree(session)
    save(session, "https://a.com", goal_id=quarter.id)
    save(session, "https://b.com", days_old=10)
    calendar.put("primary", meeting("Investor call", 23, "13:00", "14:00"))
    cycle.run(session)
    session.commit()
    t = client.post("/v1/tasks", json={"title": "Split parity", "goal_id": week.id}).json()
    client.put("/v1/days/2026-11-23/top-three", json={"task_ids": [t["id"]]})
    client.patch(f"/v1/tasks/{t['id']}", json={"done": True})
    client.put("/v1/reviews/2026-11-16/answers", json={"answers": {"next_top": "Ship parity"}})
    client.post("/v1/reviews/2026-11-16/close")
    client.post("/v1/days/2026-11-23/shutdown", json={"learned_line": "Raft needs a quorum"})
    before = {p: client.get(p).json() for p in PATHS}
    r = client.get("/v1/export")
    assert r.headers["content-disposition"].startswith('attachment; filename="compass-export-')
    data = r.json()
    assert data["tables"]["goals"] and data["tables"]["time_blocks"]

    db.configure(f"sqlite:///{tmp_path / 'restored.db'}")
    migrate.upgrade()
    with db.SessionLocal() as s:
        assert export.load(s, data) == sum(len(rows) for rows in data["tables"].values())
        s.commit()
    after = {p: client.get(p).json() for p in PATHS}
    assert after == before

    with db.SessionLocal() as s, pytest.raises(ValueError, match="not empty"):
        export.load(s, data)
