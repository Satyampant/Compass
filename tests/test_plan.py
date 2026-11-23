from datetime import date

from app.modules.day.models import DailyLog

TOMORROW = "2026-11-24"


def task(client, title, day="2026-11-23", minutes=30):
    return client.post(
        "/v1/tasks", json={"title": title, "planned_date": day, "estimate_min": minutes}
    ).json()


def plan(client, decisions, top=()):
    return client.post(f"/v1/days/{TOMORROW}/plan", json={"decisions": decisions, "top": list(top)})


def test_four_open_tasks_need_a_decision_each(client, session, fake_clock):
    a, b, c, d = (task(client, t) for t in ("a", "b", "c", "d"))
    done = task(client, "done")
    client.patch(f"/v1/tasks/{done['id']}", json={"done": True})
    already = task(client, "already tomorrow", day=TOMORROW)
    draft = client.get(f"/v1/days/{TOMORROW}/plan").json()
    assert [t["title"] for t in draft["open"]] == ["a", "b", "c", "d"]
    assert [t["title"] for t in draft["planned"]] == ["already tomorrow"]

    three = [
        {"task_id": a["id"], "action": "tomorrow"},
        {"task_id": b["id"], "action": "reschedule", "to": "2026-11-27"},
        {"task_id": c["id"], "action": "drop"},
    ]
    r = plan(client, three)
    assert r.status_code == 422 and r.json()["detail"] == "decide on every open task first: d"
    assert session.get(DailyLog, date(2026, 11, 24)) is None

    r = plan(client, [*three, {"task_id": d["id"], "action": "tomorrow"}], [already["id"], a["id"]])
    assert r.status_code == 200
    assert [t["title"] for t in r.json()["top"]] == ["already tomorrow", "a"]
    session.expire_all()
    assert session.get(DailyLog, date(2026, 11, 24)).planned_at is not None

    assert client.get(f"/v1/days/{TOMORROW}/plan").json()["open"] == []
    week = client.get("/v1/week").json()
    titles = {d["date"]: [t["title"] for t in d["tasks"]] for d in week["days"]}
    assert titles["2026-11-23"] == ["done"]
    assert titles["2026-11-24"] == ["already tomorrow", "a", "d"]
    assert titles["2026-11-27"] == ["b"]
    assert "c" not in str(client.get("/v1/today").json()["tasks"])


def test_bad_decisions(client, fake_clock):
    a = task(client, "a")
    assert plan(client, [{"task_id": a["id"], "action": "keep"}]).status_code == 422
    r = plan(client, [{"task_id": a["id"], "action": "reschedule"}])
    assert r.json()["detail"] == "reschedule needs a date from the planned day on"
    r = plan(
        client, [{"task_id": a["id"], "action": "tomorrow"}, {"task_id": 999, "action": "drop"}]
    )
    assert r.status_code == 422
    assert plan(client, [{"task_id": a["id"], "action": "tomorrow"}], [999]).status_code == 422


def test_nothing_open_plans_at_once(client, fake_clock):
    assert plan(client, []).status_code == 200
