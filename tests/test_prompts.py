from datetime import UTC, datetime

from app.modules.planning import service

IST = 3  # 08:30 IST is 03:00 UTC


def on(fake_clock, y, m, d):
    fake_clock.set(datetime(y, m, d, IST, tzinfo=UTC))


def test_quarter_prompt_is_showing_on_24_december(client, session, fake_clock):
    on(fake_clock, 2026, 12, 24)
    labels = [p["label"] for p in client.get("/v1/planning/prompts").json()]
    assert labels == ["2027", "Q1 2027"]


def test_prompts_open_on_their_dates(client, fake_clock):
    on(fake_clock, 2026, 11, 30)
    assert client.get("/v1/planning/prompts").json() == []
    on(fake_clock, 2026, 12, 1)
    assert [p["horizon"] for p in client.get("/v1/planning/prompts").json()] == ["year"]
    on(fake_clock, 2026, 9, 23)
    assert client.get("/v1/planning/prompts").json() == []
    on(fake_clock, 2026, 9, 24)
    assert client.get("/v1/planning/prompts").json() == [
        {"horizon": "quarter", "starts": "2026-10-01", "label": "Q4 2026"}
    ]


def test_prompt_closes_once_the_period_has_goals(client, session, fake_clock):
    on(fake_clock, 2026, 12, 24)
    theme = service.create_goal(session, "year", "Theme", datetime(2027, 1, 1).date())
    session.commit()
    assert [p["label"] for p in client.get("/v1/planning/prompts").json()] == ["Q1 2027"]
    r = client.post(
        "/v1/goals",
        json={
            "horizon": "quarter",
            "title": "Q",
            "parent_id": theme.id,
            "on": "2027-01-01",
            "key_results": [{"title": "k", "target": 1}],
        },
    )
    assert r.status_code == 201
    assert client.get("/v1/planning/prompts").json() == []
