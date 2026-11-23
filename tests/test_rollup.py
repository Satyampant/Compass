from datetime import date

from sqlalchemy import select

from app.kernel import scheduler
from app.modules.day.service import create_task
from app.modules.review import rollup
from app.modules.review.models import DayStats
from tests.test_protect import ist

D = date(2026, 11, 23)


def test_running_twice_for_the_same_date_leaves_one_row(session, fake_clock):
    create_task(session, "a", D, 60)
    rollup.rollup(session, D)
    create_task(session, "b", D, 30)
    rollup.rollup(session, D)
    rows = session.scalars(select(DayStats)).all()
    assert len(rows) == 1 and rows[0].planned_min == 90


def test_rollup_runs_at_2330_or_at_next_wake_for_the_right_day(session, fake_clock):
    create_task(session, "a", D, 60)
    session.commit()
    fake_clock.set(ist(24, "08:00"))  # slept through 23:30
    scheduler.tick()
    session.expire_all()
    assert [r.day for r in session.scalars(select(DayStats))] == [D]
    scheduler.tick()
    assert len(session.scalars(select(DayStats)).all()) == 1
