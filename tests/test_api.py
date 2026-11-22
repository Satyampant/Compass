from datetime import UTC, datetime


def capture(client, text, key=None, **extra):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post("/v1/captures", json={"text": text, **extra}, headers=headers)


def test_capture_link_returns_202_and_item(client, fake_clock):
    r = capture(client, "https://raft.github.io", key="k1")
    assert r.status_code == 202
    assert r.json()["outcome"] == "item"
    items = client.get("/v1/learning-items?state=inbox").json()
    assert [i["id"] for i in items] == [r.json()["item_id"]]
    assert items[0]["actions"] == ["book", "let_go"]


def test_capture_same_key_twice(client, fake_clock):
    a = capture(client, "https://a.com", key="k").json()
    b = capture(client, "https://a.com", key="k").json()
    assert a["capture_id"] == b["capture_id"]


def test_capture_rejects_empty_and_bad_kind(client):
    assert capture(client, "  ").status_code == 422
    assert capture(client, "x", kind="poem").status_code == 422


def test_resolve_pending_text(client, fake_clock):
    r = capture(client, "CRDT reading").json()
    assert r["outcome"] == "pending"
    r = client.post(f"/v1/captures/{r['capture_id']}/resolve", json={"kind": "note"}).json()
    assert r["outcome"] == "note" and r["title"] == "CRDT reading"
    assert client.post("/v1/captures/999/resolve", json={"kind": "note"}).status_code == 404


def test_transition_book_defaults_to_next_slot(client, fake_clock):
    item_id = capture(client, "https://a.com").json()["item_id"]
    r = client.post(f"/v1/learning-items/{item_id}/transitions", json={"action": "book"})
    assert r.status_code == 200
    # Monday 06:00 IST: next slot is Monday 16:00 IST = 10:30 UTC
    assert r.json()["booked_for"].startswith("2026-11-23T10:30")
    assert r.json()["actions"] == ["start", "unbook", "let_go"]


def test_transition_with_chosen_time(client, fake_clock):
    item_id = capture(client, "https://a.com").json()["item_id"]
    when = datetime(2026, 11, 25, 12, 0, tzinfo=UTC).isoformat()
    r = client.post(
        f"/v1/learning-items/{item_id}/transitions", json={"action": "book", "booked_for": when}
    )
    assert r.json()["booked_for"].startswith("2026-11-25T12:00")


def test_invalid_transition_is_a_clear_error(client, fake_clock):
    item_id = capture(client, "https://a.com").json()["item_id"]
    r = client.post(f"/v1/learning-items/{item_id}/transitions", json={"action": "finish"})
    assert r.status_code == 409
    assert r.json()["detail"] == "cannot finish an item that is inbox"
    assert (
        client.post("/v1/learning-items/99/transitions", json={"action": "book"}).status_code == 404
    )


def test_edit_item_with_version(client, fake_clock):
    item_id = capture(client, "https://a.com").json()["item_id"]
    r = client.patch(f"/v1/learning-items/{item_id}", json={"estimate_min": 45, "version": 1})
    assert r.json()["estimate_min"] == 45 and r.json()["version"] == 2
    stale = client.patch(f"/v1/learning-items/{item_id}", json={"title": "x", "version": 1})
    assert stale.status_code == 409


def test_tasks_create_tick_move(client, fake_clock):
    r = client.post("/v1/tasks", json={"title": "Investor call", "estimate_min": 60})
    assert r.status_code == 201
    task = r.json()
    assert task["planned_date"] == "2026-11-23"
    r = client.patch(f"/v1/tasks/{task['id']}", json={"done": True})
    assert r.json()["done_at"] is not None
    r = client.patch(f"/v1/tasks/{task['id']}", json={"planned_date": "2026-11-26", "done": False})
    assert r.json()["planned_date"] == "2026-11-26" and r.json()["done_at"] is None
    assert client.patch("/v1/tasks/99", json={"done": True}).status_code == 404
    stale = client.patch(f"/v1/tasks/{task['id']}", json={"title": "y", "version": 1})
    assert stale.status_code == 409
