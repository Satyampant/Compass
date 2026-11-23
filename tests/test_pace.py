from datetime import UTC, date, datetime

from app.modules.planning import trace

Q4 = (date(2026, 10, 1), date(2026, 12, 31))


def test_day_54_of_92():
    today = date(2026, 11, 23)
    share = trace.pace(*Q4, today)
    assert round(share * 92) == 54 and round(share, 3) == 0.587
    assert trace.pace_status(0.51, share, 10, 20) == "on_track"
    assert trace.pace_status(0.45, share, 10, 20) == "at_risk"
    assert trace.pace_status(0.35, share, 10, 20) == "behind"
    assert trace.pace(*Q4, date(2027, 2, 1)) == 1 and trace.pace(*Q4, date(2026, 9, 1)) == 0


def test_quarter_goal_api_shows_pace(client, fake_clock):
    fake_clock.set(datetime(2026, 11, 23, 3, tzinfo=UTC))
    year = client.post("/v1/goals", json={"horizon": "year", "title": "T"}).json()
    q = client.post(
        "/v1/goals",
        json={
            "horizon": "quarter",
            "title": "Q",
            "parent_id": year["id"],
            "key_results": [{"title": "k", "target": 100, "current": 51}],
        },
    ).json()
    assert q["pace_status"] == "on_track" and round(q["pace"], 3) == 0.587
    kr = q["key_results"][0]["id"]
    client.patch(f"/v1/key-results/{kr}", json={"current": 35})
    assert client.get("/v1/goals?horizon=quarter").json()[0]["pace_status"] == "behind"
    assert year["pace"] is None
