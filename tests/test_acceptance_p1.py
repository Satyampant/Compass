"""PRD 'accepted when' checks for phase 1, in the PRD's words.

Checks that need the phone or five real days are in docs/acceptance-p1.md. Pace (on track
on day 54 of 92) is phase 3, and blocks on Today are phase 2.
"""

import time
from datetime import UTC, date, datetime, timedelta

from app.modules.capture import service as capture
from app.modules.day.service import create_task
from app.modules.planning import service as planning
from app.modules.planning.service import KeyResultIn
from tests.test_bot_commands import ask
from tests.test_brief import ME, tg  # noqa: F401

MONDAY = date(2026, 11, 23)


def tree(session):
    """Three themes, five quarter goals, ten milestones and three outcomes."""
    themes = [planning.create_goal(session, "year", f"Theme {n}", MONDAY) for n in range(3)]
    quarters = [
        planning.create_goal(
            session,
            "quarter",
            f"Goal {n}",
            MONDAY,
            parent_id=themes[n % 3].id,
            key_results=[KeyResultIn("KR", 10, n)],
            short=f"G{n}",
            color=n + 1,
        )
        for n in range(5)
    ]
    months = [
        planning.create_goal(
            session, "month", f"Milestone {n}", MONDAY, parent_id=quarters[n % 5].id
        )
        for n in range(10)
    ]
    weeks = [
        planning.create_goal(session, "week", f"Outcome {n}", MONDAY, parent_id=months[n].id)
        for n in range(3)
    ]
    session.commit()
    return themes, quarters, months, weeks


def test_from_any_task_on_today_the_year_theme_is_one_click_away(client, session, fake_clock):
    themes, quarters, months, weeks = tree(session)
    for goal in (weeks[0], months[4], quarters[2]):
        task = client.post("/v1/tasks", json={"title": "t", "goal_id": goal.id}).json()
        steps = client.get(f"/v1/goals/{task['goal_id']}/trace").json()
        assert steps[0]["horizon"] == "year"


def test_weekly_outcome_cannot_be_saved_without_a_parent_milestone(client, session, fake_clock):
    themes, *_ = tree(session)
    for parent in (None, themes[0].id):
        r = client.post("/v1/goals", json={"horizon": "week", "title": "x", "parent_id": parent})
        assert r.status_code == 422


def test_day_planned_the_evening_before_opens_with_focus_and_top_three(client, session, fake_clock):
    *_, weeks = tree(session)
    fake_clock.set(datetime(2026, 11, 23, 14, 30, tzinfo=UTC))  # Monday 20:00 IST
    a = client.post("/v1/tasks", json={"title": "Split parity", "goal_id": weeks[0].id}).json()
    b = client.post("/v1/tasks", json={"title": "Investor call"}).json()
    plan = {
        "decisions": [
            {"task_id": a["id"], "action": "tomorrow"},
            {"task_id": b["id"], "action": "tomorrow"},
        ],
        "top": [a["id"], b["id"]],
    }
    assert client.post("/v1/days/2026-11-24/plan", json=plan).status_code == 200
    fake_clock.set(datetime(2026, 11, 24, 2, 30, tzinfo=UTC))  # Tuesday 08:00 IST
    today = client.get("/v1/today").json()
    assert today["focus"]["task"]["title"] == "Split parity"
    assert [s["horizon"] for s in today["focus"]["trace"]] == ["year", "quarter", "month", "week"]
    assert [(t["title"], t["top_rank"]) for t in today["tasks"]] == [
        ("Split parity", 1),
        ("Investor call", 2),
    ]


def test_ticking_the_fourth_shutdown_step_marks_the_day_closed(client, fake_clock):
    client.post("/v1/days/2026-11-23/shutdown", json={"learned_line": "Raft needs a quorum"})
    assert client.get("/v1/today").json()["closed_at"] is not None


def test_today_loads_in_under_half_a_second(client, session, fake_clock):
    themes, quarters, months, weeks = tree(session)
    goals = [*quarters, *months, *weeks, None]
    for n in range(60):
        goal = goals[n % len(goals)]
        create_task(session, f"Task {n}", MONDAY - timedelta(days=n % 3), 30, goal and goal.id)
    for n in range(150):
        capture.capture(session, text=f"https://site{n}.example.com", channel="web", key=str(n))
    session.commit()
    client.get("/v1/today")
    start = time.perf_counter()
    assert client.get("/v1/today").status_code == 200
    assert time.perf_counter() - start < 0.5


def test_dragging_a_three_hour_task_updates_both_day_totals(client, fake_clock):
    t = client.post(
        "/v1/tasks", json={"title": "Parity", "estimate_min": 180, "planned_date": "2026-11-23"}
    ).json()
    client.patch(f"/v1/tasks/{t['id']}", json={"planned_date": "2026-11-26"})
    days = client.get("/v1/week").json()["days"]
    assert (days[0]["planned_min"], days[3]["planned_min"]) == (0, 180)


def test_a_44_hour_week_against_40_shows_a_warning(client, fake_clock):
    for day in ("2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"):
        client.post("/v1/tasks", json={"title": "Work", "estimate_min": 660, "planned_date": day})
    week = client.get("/v1/week").json()
    assert week["planned_min"] == 44 * 60 and week["capacity_min"] == 40 * 60 and week["over"]


def test_an_item_cannot_reach_learned_without_the_note(client, fake_clock):
    item = client.post("/v1/captures", json={"text": "https://raft.github.io"}).json()["item_id"]
    for action in ("book", "start"):
        client.post(f"/v1/learning-items/{item}/transitions", json={"action": action})
    r = client.post(f"/v1/learning-items/{item}/transitions", json={"action": "finish"})
    assert r.status_code == 409


def test_bot_answers_today_and_queue(session, tg):  # noqa: F811
    assert ask(session, tg, "/today")["text"].startswith("No top three yet.")
    assert ask(session, tg, "/queue")["text"].startswith("Inbox: 0 waiting")
