"""Every screen loads in under half a second, with a busy year of data (PRD section 10)."""

import time
from datetime import date, timedelta

from app.modules.autopilot import cycle
from app.modules.capture import service as capture
from app.modules.day.models import DailyLog
from app.modules.day.service import create_task, set_top
from app.modules.planning import service as planning
from app.modules.planning.service import KeyResultIn
from tests.test_protect import meeting

TODAY = date(2026, 11, 23)
SCREENS = {
    "today": ["/v1/today", "/v1/goals?horizon=year", "/v1/calendar", "/v1/status"],
    "queue": ["/v1/learning-items?state=inbox,booked,learning,learned", "/v1/reviews/history"],
    "week": ["/v1/week", "/v1/goals?horizon=week", "/v1/goals?horizon=month"],
    "month": ["/v1/goals?horizon=month", "/v1/goals?horizon=quarter"],
    "quarter": ["/v1/goals?horizon=quarter", "/v1/goals?horizon=year", "/v1/planning/prompts"],
    "year": ["/v1/goals?horizon=year", "/v1/goals?horizon=quarter"],
    "review": ["/v1/reviews/current", "/v1/reviews/history"],
    "plan": ["/v1/days/2026-11-24/plan"],
    "status": ["/v1/status"],
    "settings": ["/v1/settings"],
}


def busy_year(session, calendar):
    themes = [planning.create_goal(session, "year", f"Theme {n}", TODAY) for n in range(3)]
    quarters = [
        planning.create_goal(
            session,
            "quarter",
            f"Q{n}",
            TODAY,
            parent_id=themes[n % 3].id,
            key_results=[KeyResultIn("k", 10, n)] * 3,
            short=f"G{n}",
            color=n + 1,
        )
        for n in range(5)
    ]
    months = [
        planning.create_goal(session, "month", f"M{n}", TODAY, parent_id=quarters[n % 5].id)
        for n in range(12)
    ]
    weeks = [
        planning.create_goal(session, "week", f"W{n}", TODAY, parent_id=months[n].id)
        for n in range(3)
    ]
    goals = [*quarters, *months, *weeks, None]
    for d in range(300):
        day = TODAY - timedelta(days=d)
        tasks = [
            create_task(
                session,
                f"Task {d}.{n}",
                day,
                30 + n * 15,
                (goals[(d + n) % len(goals)] or type("", (), {"id": None})).id,
            )
            for n in range(4)
        ]
        set_top(session, day, [t.id for t in tasks[:3]])
        session.add(DailyLog(day=day))
    for n in range(400):
        capture.capture(session, text=f"https://site{n}.example.com/p", channel="web", key=str(n))
    for n in range(30):
        calendar.put("primary", meeting(f"Call {n}", 23 + n % 7, "11:00", "12:00"))
    cycle.run(session)
    session.commit()


def test_every_screen_loads_in_under_half_a_second(client, session, fake_clock, calendar):
    busy_year(session, calendar)
    for paths in SCREENS.values():
        for p in paths:
            client.get(p)  # warm
    slow = {}
    for screen, paths in SCREENS.items():
        start = time.perf_counter()
        for p in paths:
            assert client.get(p).status_code == 200, p
        took = time.perf_counter() - start
        if took >= 0.5:
            slow[screen] = round(took, 3)
    assert slow == {}
