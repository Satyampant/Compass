def theme(client, title="OS for traders", **extra):
    return client.post("/v1/goals", json={"horizon": "year", "title": title, **extra})


def tree(client):
    year = theme(client).json()
    quarter = client.post(
        "/v1/goals",
        json={
            "horizon": "quarter",
            "title": "Backtest v1",
            "parent_id": year["id"],
            "short": "Backtest",
            "color": 1,
            "key_results": [
                {"title": "Parity", "target": 500, "current": 100, "unit": "strategies"}
            ],
        },
    ).json()
    month = client.post(
        "/v1/goals",
        json={
            "horizon": "month",
            "title": "Parity green",
            "parent_id": quarter["id"],
            "due_date": "2026-11-30",
        },
    ).json()
    week = client.post(
        "/v1/goals", json={"horizon": "week", "title": "Corp actions", "parent_id": month["id"]}
    ).json()
    return year, quarter, month, week


def test_create_and_list_a_horizon(client, fake_clock):
    year, quarter, month, week = tree(client)
    assert quarter["progress"] == 0.2 and quarter["key_results"][0]["unit"] == "strategies"
    assert quarter["period_start"] == "2026-10-01"
    listed = client.get("/v1/goals?horizon=quarter").json()
    assert [g["id"] for g in listed] == [quarter["id"]]
    assert client.get("/v1/goals?horizon=quarter&on=2027-01-10").json() == []
    assert client.get("/v1/goals?horizon=month").json()[0]["due_date"] == "2026-11-30"
    assert client.get("/v1/goals?horizon=decade").status_code == 422


def test_rule_breaks_are_422(client, fake_clock):
    r = client.post("/v1/goals", json={"horizon": "week", "title": "Orphan"})
    assert r.status_code == 422 and r.json()["detail"] == "a week goal needs a month parent"
    for i in range(3):
        theme(client, f"T{i}")
    assert theme(client, "T4").json()["detail"] == "at most 3 themes a year"
    assert client.post("/v1/goals", json={"horizon": "year", "title": ""}).status_code == 422


def test_edit_goal_and_mark_done(client, fake_clock):
    year, quarter, month, week = tree(client)
    r = client.patch(f"/v1/goals/{week['id']}", json={"done": True, "version": 1}).json()
    assert r["done"] and r["progress"] == 1.0 and r["version"] == 2
    stale = client.patch(f"/v1/goals/{week['id']}", json={"title": "x", "version": 1})
    assert stale.status_code == 409
    r = client.patch(f"/v1/goals/{month['id']}", json={"due_date": None}).json()
    assert r["due_date"] is None
    assert client.patch("/v1/goals/999", json={"title": "x"}).status_code == 404


def test_key_results_add_and_update(client, fake_clock):
    year, quarter, month, week = tree(client)
    r = client.post(f"/v1/goals/{quarter['id']}/key-results", json={"title": "Beta", "target": 50})
    assert r.status_code == 201
    kr_id = quarter["key_results"][0]["id"]
    r = client.patch(f"/v1/key-results/{kr_id}", json={"current": 500, "version": 1})
    assert r.json()["current"] == 500 and r.json()["version"] == 2
    got = client.get("/v1/goals?horizon=quarter").json()[0]
    assert got["progress"] == 0.5
    assert (
        client.patch(f"/v1/key-results/{kr_id}", json={"current": 1, "version": 1}).status_code
        == 409
    )
    assert client.patch("/v1/key-results/999", json={"current": 1}).status_code == 404
    r = client.post(f"/v1/goals/{year['id']}/key-results", json={"title": "x", "target": 1})
    assert r.status_code == 422


def test_trace(client, fake_clock):
    year, quarter, month, week = tree(client)
    steps = client.get(f"/v1/goals/{week['id']}/trace").json()
    assert [s["horizon"] for s in steps] == ["year", "quarter", "month", "week"]
    assert steps[1]["short"] == "Backtest"
    assert client.get("/v1/goals/999/trace").status_code == 404


def test_deleting_a_goal_unties_its_work_and_asks_children_for_a_parent(client, fake_clock):
    year, quarter, month, week = tree(client)
    task = client.post("/v1/tasks", json={"title": "t", "goal_id": month["id"]}).json()
    item = client.post(
        "/v1/captures", json={"text": "https://a.com", "goal_id": month["id"]}
    ).json()
    assert client.delete(f"/v1/goals/{month['id']}").status_code == 204
    orphan = client.get("/v1/goals?horizon=week").json()[0]
    assert orphan["draft"] is True and orphan["parent_id"] is None
    assert client.get("/v1/today").json()["tasks"][0]["goal_id"] is None
    items = client.get("/v1/learning-items?state=inbox").json()
    assert [i["goal_id"] for i in items if i["id"] == item["item_id"]] == [None]
    assert task["goal_id"] == month["id"]
    new = client.post(
        "/v1/goals", json={"horizon": "month", "title": "M2", "parent_id": quarter["id"]}
    ).json()
    r = client.patch(f"/v1/goals/{orphan['id']}", json={"parent_id": new["id"]}).json()
    assert r["draft"] is False and r["parent_id"] == new["id"]


def test_deleting_a_quarter_goal_with_key_results(client, fake_clock):
    year, quarter, month, week = tree(client)
    r = client.delete(f"/v1/goals/{quarter['id']}")
    assert r.status_code == 204
    assert client.get("/v1/goals?horizon=month").json()[0]["draft"] is True
