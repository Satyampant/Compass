from datetime import date

from app.modules.day.service import create_task
from app.modules.planning import service, trace
from app.modules.planning.service import KeyResultIn

DAY = date(2026, 11, 23)


def test_task_four_levels_down_returns_full_chain(session, fake_clock):
    year = service.create_goal(session, "year", "OS for traders", DAY)
    quarter = service.create_goal(
        session, "quarter", "Backtest v1", DAY, parent_id=year.id, key_results=[KeyResultIn("x", 1)]
    )
    month = service.create_goal(session, "month", "Parity green", DAY, parent_id=quarter.id)
    week = service.create_goal(session, "week", "Corporate actions", DAY, parent_id=month.id)
    task = create_task(session, "Split parity", DAY)
    task.goal_id = week.id
    untied = create_task(session, "Gym", DAY)
    session.flush()
    got = trace.task_chain(session, task.id)
    assert [(g.horizon, g.title) for g in got] == [
        ("year", "OS for traders"),
        ("quarter", "Backtest v1"),
        ("month", "Parity green"),
        ("week", "Corporate actions"),
    ]
    assert trace.task_chain(session, untied.id) == []
    assert [g.id for g in trace.chain(session, month.id)] == [year.id, quarter.id, month.id]


def test_progress_rolls_up(session, fake_clock):
    year = service.create_goal(session, "year", "Theme", DAY)
    krs = [KeyResultIn("a", 500, 310), KeyResultIn("b", 10, 10), KeyResultIn("c", 50, 100)]
    q1 = service.create_goal(session, "quarter", "Q1", DAY, parent_id=year.id, key_results=krs)
    q2 = service.create_goal(
        session, "quarter", "Q2", DAY, parent_id=year.id, key_results=[KeyResultIn("d", 4, 1)]
    )
    month = service.create_goal(session, "month", "M", DAY, parent_id=q1.id)
    assert round(trace.progress(session, q1), 3) == round((0.62 + 1 + 1) / 3, 3)
    assert trace.progress(session, q2) == 0.25
    assert round(trace.progress(session, year), 3) == round(((0.62 + 2) / 3 + 0.25) / 2, 3)
    assert trace.progress(session, month) == 0.0
    month.done_at = fake_clock.now()
    assert trace.progress(session, month) == 1.0
