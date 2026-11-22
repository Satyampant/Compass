from app.modules.autopilot import brief, resurface


def test_today_lists_tasks_and_revisit(client, session, fake_clock):
    r = client.get("/v1/today").json()
    assert r["tasks"] == [] and r["revisit"] == [] and r["has_items"] is False
    client.post("/v1/tasks", json={"title": "Investor call"})
    client.post("/v1/captures", json={"text": "https://a.com"})
    fake_clock.advance(days=3)
    resurface.catch_up(session, fake_clock.now().date())
    session.commit()
    r = client.get("/v1/today").json()
    assert [t["title"] for t in r["tasks"]] == ["Investor call"]
    assert [i["url"] for i in r["revisit"]] == ["https://a.com"]
    assert r["inbox_count"] == 1 and r["has_items"] is True


def test_revisit_card_matches_brief(client, session, fake_clock):
    for n in range(5):
        client.post("/v1/captures", json={"text": f"https://x.com/{n}"})
    fake_clock.advance(days=3)
    resurface.catch_up(session, fake_clock.now().date())
    session.commit()
    card = [i["id"] for i in client.get("/v1/today").json()["revisit"]]
    rows = brief.build(session)[0].buttons
    assert len(card) == 3
    assert [int(row[0][1].split(":")[2]) for row in rows] == card


def test_undone_task_from_yesterday_stays_until_decided(client, fake_clock):
    client.post("/v1/tasks", json={"title": "old"})
    fake_clock.advance(days=1)
    assert [t["title"] for t in client.get("/v1/today").json()["tasks"]] == ["old"]
    fake_clock.advance(days=-1)
    done = client.post("/v1/tasks", json={"title": "done one"}).json()
    client.patch(f"/v1/tasks/{done['id']}", json={"done": True})
    fake_clock.advance(days=1)
    assert [t["title"] for t in client.get("/v1/today").json()["tasks"]] == ["old"]
