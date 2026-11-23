from datetime import date

from app.modules.planning import service as planning
from app.modules.planning.service import KeyResultIn

DAY = date(2026, 11, 23)


def task(client, title, **extra):
    return client.post("/v1/tasks", json={"title": title, **extra}).json()


def chain(session):
    year = planning.create_goal(session, "year", "OS for traders", DAY)
    quarter = planning.create_goal(
        session,
        "quarter",
        "Backtest v1",
        DAY,
        parent_id=year.id,
        key_results=[KeyResultIn("Parity", 500)],
    )
    month = planning.create_goal(session, "month", "Parity green", DAY, parent_id=quarter.id)
    week = planning.create_goal(session, "week", "Corp actions", DAY, parent_id=month.id)
    session.commit()
    return week


def test_rank_three_and_focus_with_trace(client, session, fake_clock):
    week = chain(session)
    a = task(client, "Split parity", goal_id=week.id)
    b = task(client, "Investor call")
    c = task(client, "License review")
    task(client, "Gym")
    r = client.put("/v1/days/2026-11-23/top-three", json={"task_ids": [a["id"], b["id"], c["id"]]})
    assert [t["top_rank"] for t in r.json()] == [1, 2, 3]
    today = client.get("/v1/today").json()
    assert [t["title"] for t in today["tasks"]][:3] == [
        "Split parity",
        "Investor call",
        "License review",
    ]
    assert today["focus"]["task"]["id"] == a["id"] and today["top_limit"] == 3
    assert [s["horizon"] for s in today["focus"]["trace"]] == ["year", "quarter", "month", "week"]

    client.patch(f"/v1/tasks/{a['id']}", json={"done": True})
    today = client.get("/v1/today").json()
    assert today["focus"]["task"]["id"] == b["id"] and today["focus"]["trace"] == []


def test_replacing_a_rank_and_moving_a_task(client, session, fake_clock):
    a, b, c, d = (task(client, t) for t in "abcd")
    client.put("/v1/days/2026-11-23/top-three", json={"task_ids": [a["id"], b["id"], c["id"]]})
    r = client.put("/v1/days/2026-11-23/top-three", json={"task_ids": [a["id"], d["id"], c["id"]]})
    assert r.status_code == 200
    ranks = {t["title"]: t["top_rank"] for t in client.get("/v1/today").json()["tasks"]}
    assert ranks == {"a": 1, "d": 2, "c": 3, "b": None}
    moved = client.patch(f"/v1/tasks/{a['id']}", json={"planned_date": "2026-11-24"}).json()
    assert moved["top_rank"] is None
    assert client.get("/v1/today").json()["focus"]["task"]["title"] == "d"


def test_top_three_errors(client, fake_clock):
    a = task(client, "a")
    put = lambda ids: client.put("/v1/days/2026-11-23/top-three", json={"task_ids": ids})  # noqa: E731
    assert put([a["id"], a["id"]]).status_code == 422
    assert put([999]).status_code == 404
    assert put([]).status_code == 200
    assert client.get("/v1/today").json()["focus"] is None


def test_ranked_for_tomorrow_moves_the_task(client, fake_clock):
    a = task(client, "a")
    client.put("/v1/days/2026-11-24/top-three", json={"task_ids": [a["id"]]})
    assert client.get("/v1/today").json()["tasks"] == []
