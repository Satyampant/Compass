from datetime import date

import pytest

from app.kernel import scheduler
from app.modules.capture import service as capture
from app.modules.day.service import create_task, set_top
from app.modules.learning import lifecycle
from app.modules.notify import bot
from app.modules.notify import service as notify
from app.modules.review import service
from tests.fakes import FakeTelegram
from tests.test_goal_links import tree
from tests.test_protect import ist

MON = date(2026, 11, 23)
WEEK = "/v1/reviews/2026-11-23"


def week_with_work(session, fake_clock):
    year, quarter, week = tree(session)
    a = create_task(session, "Split parity", MON, 180, goal_id=week.id)
    b = create_task(session, "Investor call", MON, 60)
    c = create_task(session, "Cap table", date(2026, 11, 24), 30)
    set_top(session, MON, [a.id, b.id])
    set_top(session, date(2026, 11, 24), [c.id])
    a.done_at = fake_clock.now()
    for n in range(3):
        capture.capture(session, text=f"https://x{n}.com", channel="web", key=str(n))
    old = capture.capture(session, text="https://old.com", channel="web", key="old").item
    lifecycle.transition(session, old, "expire")
    session.commit()
    return year, quarter, week, a, b, c


def test_review_numbers_and_lists(client, session, fake_clock):
    *_, a, b, c = week_with_work(session, fake_clock)
    r = client.get(WEEK).json()
    n = r["numbers"]
    assert (n["top_done"], n["top_planned"]) == (1, 3)
    assert (n["aligned_min"], n["planned_min"]) == (180, 270)
    assert (n["captured"], n["closed"]) == (4, 1)
    assert n["hours_by_goal"][0]["tag"]["title"] == "Backtest v1"
    assert (n["hours_by_goal"][0]["planned_min"], n["hours_by_goal"][0]["done_min"]) == (180, 180)
    assert n["hours_by_goal"][-1] == {"tag": None, "planned_min": 90, "done_min": 0}
    assert [i["url"] for i in r["expired"]] == ["https://old.com"]
    assert len(r["oldest"]) == 3 and r["week_number"] == 48


def test_closing_freezes_numbers_and_drafts_next_week(client, session, fake_clock):
    *_, a, b, c = week_with_work(session, fake_clock)
    answers = {
        "moved": "Fee model merged",
        "off_course": "Calls",
        "still_matter": "",
        "next_top": "1. Corporate actions parity  2. Metrics pack 3. K8s lab",
    }
    assert client.put(f"{WEEK}/answers", json={"answers": answers}).status_code == 200
    r = client.post(f"{WEEK}/close").json()
    assert r["closed_at"] and r["numbers"]["top_done"] == 1
    assert [(g["title"], g["draft"], g["parent_id"]) for g in r["drafts"]] == [
        ("Corporate actions parity", True, None),
        ("Metrics pack", True, None),
        ("K8s lab", True, None),
    ]
    assert r["drafts"][0]["period_start"] == "2026-11-30"

    # Completing a week-48 task after closing does not change week 48's numbers.
    client.patch(f"/v1/tasks/{b.id}", json={"done": True})
    client.post("/v1/tasks", json={"title": "late", "planned_date": "2026-11-25"})
    assert client.get(WEEK).json()["numbers"] == r["numbers"]
    assert client.post(f"{WEEK}/close").status_code == 409
    assert client.put(f"{WEEK}/answers", json={"answers": answers}).status_code == 409


def test_draft_takes_a_milestone(client, session, fake_clock):
    year, quarter, week, *_ = week_with_work(session, fake_clock)
    client.put(f"{WEEK}/answers", json={"answers": {"next_top": "Ship parity"}})
    draft = client.post(f"{WEEK}/close").json()["drafts"][0]
    assert (
        client.patch(f"/v1/goals/{draft['id']}", json={"parent_id": quarter.id}).status_code == 422
    )
    r = client.patch(f"/v1/goals/{draft['id']}", json={"parent_id": week.parent_id}).json()
    assert r["draft"] is False and r["parent_id"] == week.parent_id
    assert (
        client.patch(f"/v1/goals/{week.id}", json={"parent_id": week.parent_id}).status_code == 200
    )


@pytest.mark.parametrize(
    "text,lines",
    [
        ("1. a  2. b  3. c", ["a", "b", "c"]),
        ("a\nb\n\nc\nd", ["a", "b", "c"]),
        ("- a\n- b", ["a", "b"]),
        ("", []),
    ],
)
def test_outcome_lines(text, lines):
    assert service.outcome_lines(text) == lines


def test_sunday_review_is_waiting_with_a_nudge(client, session, fake_clock, monkeypatch):
    fake = FakeTelegram()
    monkeypatch.setattr(notify, "telegram", lambda: fake)
    fake.push_message(111, "/start")
    bot.poll_once(fake)
    fake.sent.clear()
    week_with_work(session, fake_clock)
    fake_clock.set(ist(28, "19:00"))  # Saturday evening: nothing yet
    scheduler.tick()
    assert client.get(WEEK).json()["prepared_at"] is None
    fake_clock.set(ist(29, "18:05"))
    scheduler.tick()
    r = client.get(WEEK).json()
    assert r["prepared_at"] and r["numbers"]["top_planned"] == 3
    assert [m["text"] for m in fake.sent if "review" in m["text"]] == [
        "Your weekly review is ready. About 20 minutes."
    ]


def test_current_week_is_last_week_early_on_while_open(client, session, fake_clock):
    fake_clock.set(ist(24, "09:00"))  # Tuesday
    assert client.get("/v1/reviews/current").json()["week_start"] == "2026-11-16"
    client.post("/v1/reviews/2026-11-16/close")
    assert client.get("/v1/reviews/current").json()["week_start"] == "2026-11-23"
    assert client.get("/v1/reviews/2026-11-24").status_code == 422
