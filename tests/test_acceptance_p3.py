"""PRD 'accepted when' checks for phase 3, in the PRD's words.

Finishing a review in 20 minutes and closing two real weeks are in docs/acceptance-p3.md.
"""

from datetime import UTC, date, datetime

from app.kernel import scheduler
from app.modules.day.service import create_task, set_top
from tests.test_protect import ist

WEEK = "/v1/reviews/2026-11-16"


def test_after_closing_week_47_a_late_week_47_task_does_not_change_its_numbers(
    client, session, fake_clock
):
    task = create_task(session, "Split parity", date(2026, 11, 18), 120)
    set_top(session, date(2026, 11, 18), [task.id])
    session.commit()
    before = client.post(f"{WEEK}/close").json()["numbers"]
    assert (before["top_done"], before["top_planned"]) == (0, 1)
    client.patch(f"/v1/tasks/{task.id}", json={"done": True})
    assert client.get(WEEK).json()["numbers"] == before


def test_by_sunday_1800_the_review_is_ready_with_the_weeks_numbers(client, session, fake_clock):
    task = create_task(session, "Investor call", date(2026, 11, 24), 60)
    set_top(session, date(2026, 11, 24), [task.id])
    task.done_at = fake_clock.now()
    session.commit()
    fake_clock.set(ist(29, "18:00"))
    scheduler.tick()
    r = client.get("/v1/reviews/2026-11-23").json()
    assert r["prepared_at"] is not None
    assert (r["numbers"]["top_done"], r["numbers"]["top_planned"]) == (1, 1)


def test_the_fourth_answer_becomes_next_weeks_draft_outcomes(client, fake_clock):
    client.put(f"{WEEK}/answers", json={"answers": {"next_top": "1. Parity 2. Deck 3. K8s lab"}})
    drafts = client.post(f"{WEEK}/close").json()["drafts"]
    assert [(d["title"], d["period_start"], d["draft"]) for d in drafts] == [
        ("Parity", "2026-11-23", True),
        ("Deck", "2026-11-23", True),
        ("K8s lab", "2026-11-23", True),
    ]
    assert [g["title"] for g in client.get("/v1/goals?horizon=week").json()] == [
        "Parity",
        "Deck",
        "K8s lab",
    ]


def test_on_day_54_of_92_51_percent_is_on_track_and_35_is_behind(client, fake_clock):
    fake_clock.set(datetime(2026, 11, 23, 3, tzinfo=UTC))
    year = client.post("/v1/goals", json={"horizon": "year", "title": "T"}).json()
    status = []
    for current in (51, 35):
        q = client.post(
            "/v1/goals",
            json={
                "horizon": "quarter",
                "title": f"Q{current}",
                "parent_id": year["id"],
                "key_results": [{"title": "k", "target": 100, "current": current}],
            },
        ).json()
        status.append(q["pace_status"])
    assert status == ["on_track", "behind"]
