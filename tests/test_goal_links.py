from datetime import date

from app.modules.capture import service as capture
from app.modules.planning import service as planning
from app.modules.planning.service import KeyResultIn
from tests.test_resurface import run_on

DAY = date(2026, 11, 23)


def tree(session):
    year = planning.create_goal(session, "year", "OS for traders", DAY)
    quarter = planning.create_goal(
        session,
        "quarter",
        "Backtest v1",
        DAY,
        parent_id=year.id,
        key_results=[KeyResultIn("Parity", 500)],
        short="Backtest",
        color=1,
    )
    week = planning.create_goal(
        session,
        "week",
        "Corp actions",
        DAY,
        parent_id=planning.create_goal(session, "month", "Parity", DAY, parent_id=quarter.id).id,
    )
    return year, quarter, week


def test_goal_linked_item_is_still_in_inbox_on_day_30(session, fake_clock):
    fake_clock.start = fake_clock.now()
    year, quarter, week = tree(session)
    linked = capture.capture(
        session, text="https://linked.com", channel="web", key="a", goal_id=quarter.id
    ).item
    plain = capture.capture(session, text="https://plain.com", channel="web", key="b").item
    shown = [d for d in range(0, 31) if "https://linked.com" in run_on(session, fake_clock, d)]
    assert shown == [3, 7, 14]
    assert linked.state == "inbox" and linked.last_ask_at is None
    assert plain.state == "expired"


def test_capture_with_goal_and_reason(client, fake_clock, session):
    year, quarter, week = tree(session)
    session.commit()
    r = client.post(
        "/v1/captures",
        json={"text": "https://ch.com", "goal_id": quarter.id, "reason": " Faster candles "},
    ).json()
    item = client.get("/v1/learning-items?state=inbox").json()[0]
    assert item["id"] == r["item_id"] and item["reason"] == "Faster candles"
    assert item["tag"] == {
        "id": quarter.id,
        "title": "Backtest v1",
        "short": "Backtest",
        "color": 1,
    }
    r = client.post("/v1/captures", json={"text": "Call", "kind": "task", "goal_id": week.id})
    assert client.get("/v1/today").json()["tasks"][0]["tag"]["short"] == "Backtest"
    bad = client.post("/v1/captures", json={"text": "https://x.com", "goal_id": 999})
    assert bad.status_code == 422


def test_task_tied_and_untied(client, fake_clock, session):
    year, quarter, week = tree(session)
    session.commit()
    t = client.post("/v1/tasks", json={"title": "Split parity", "goal_id": week.id}).json()
    assert t["goal_id"] == week.id and t["tag"]["id"] == quarter.id
    t = client.patch(f"/v1/tasks/{t['id']}", json={"goal_id": None}).json()
    assert t["goal_id"] is None and t["tag"] is None
    t = client.patch(f"/v1/tasks/{t['id']}", json={"goal_id": year.id}).json()
    assert t["tag"]["id"] == year.id
    assert client.patch(f"/v1/tasks/{t['id']}", json={"goal_id": 999}).status_code == 422
    assert client.post("/v1/tasks", json={"title": "x", "goal_id": 999}).status_code == 422


def test_unlinking_an_item_resumes_its_schedule(client, fake_clock, session):
    fake_clock.start = fake_clock.now()
    year, quarter, week = tree(session)
    item = capture.capture(
        session, text="https://l.com", channel="web", key="a", goal_id=quarter.id
    ).item
    for d in range(0, 23):
        run_on(session, fake_clock, d)
    assert item.next_resurface_at is None
    session.commit()
    r = client.patch(f"/v1/learning-items/{item.id}", json={"goal_id": None}).json()
    assert r["goal_id"] is None
    session.expire_all()
    assert run_on(session, fake_clock, 23) == ["https://l.com"]
