def task(client, title, minutes, day):
    return client.post(
        "/v1/tasks", json={"title": title, "estimate_min": minutes, "planned_date": day}
    ).json()


def test_drag_three_hour_task_updates_both_days(client, fake_clock):
    t = task(client, "Split parity", 180, "2026-11-23")
    task(client, "Call", 60, "2026-11-26")
    week = client.get("/v1/week").json()
    assert week["start"] == "2026-11-23"
    assert [d["planned_min"] for d in week["days"]] == [180, 0, 0, 60, 0, 0, 0]
    client.patch(f"/v1/tasks/{t['id']}", json={"planned_date": "2026-11-26"})
    week = client.get("/v1/week").json()
    assert week["days"][0]["planned_min"] == 0 and week["days"][3]["planned_min"] == 240
    assert [t["title"] for t in week["days"][3]["tasks"]] == ["Split parity", "Call"]


def test_capacity_and_overbooked_week(client, fake_clock):
    for day in ("2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26", "2026-11-27"):
        task(client, "Deep work", 8 * 60, day)
    task(client, "More", 9 * 60, "2026-11-23")
    task(client, "Weekend", 2 * 60, "2026-11-28")
    week = client.get("/v1/week").json()
    assert week["days"][0]["over"] and not week["days"][1]["over"]
    assert week["days"][5]["capacity_min"] == 180 and week["days"][0]["capacity_min"] == 480
    assert week["planned_min"] == 51 * 60 and week["capacity_min"] == 2400 and week["over"]


def test_44_hour_week_warns_and_other_week_is_separate(client, fake_clock):
    for day in ("2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"):
        task(client, "Work", 11 * 60, day)
    assert client.get("/v1/week").json()["over"]
    task(client, "Next week", 60, "2026-11-30")
    nxt = client.get("/v1/week?on=2026-12-02").json()
    assert nxt["start"] == "2026-11-30" and nxt["planned_min"] == 60 and not nxt["over"]
