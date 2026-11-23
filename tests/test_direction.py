from datetime import UTC, date, datetime

from app.modules.autopilot import booking, cycle
from app.modules.capture import service as capture
from app.modules.day import blocks
from app.modules.day.models import DailyLog
from app.modules.day.service import create_task
from tests.test_goal_links import tree
from tests.test_protect import ist


def test_direction_check_agrees_with_the_metrics(client, session, fake_clock, calendar):
    year, quarter, week = tree(session)
    tied = create_task(session, "Split parity", date(2026, 11, 23), 180, goal_id=week.id)
    loose = create_task(session, "Inbox", date(2026, 11, 23), 60)
    blocks.create(session, "task", ist(23, "09:00"), ist(23, "12:00"), "P", task_id=tied.id)
    blocks.create(session, "task", ist(23, "12:00"), ist(23, "13:00"), "I", task_id=loose.id)
    for d in (21, 22, 23):
        session.add(
            DailyLog(day=date(2026, 11, d), planned_at=datetime(2026, 11, d - 1, 15, tzinfo=UTC))
        )
    item = capture.capture(session, text="https://k8s.io", channel="web", key="k").item
    cycle.run(session)
    monday = [b for b in blocks_of(session) if b.protected][0]
    fake_clock.set(monday.start)
    booking.move(session, item, "start")
    session.commit()
    d = client.get("/v1/today").json()["direction"]
    # 180 tied of 180 + 60 + 45 (the learning block holds an untied item)
    assert (d["aligned_min"], d["planned_min"]) == (180, 285)
    assert round(d["alignment"], 3) == round(180 / 285, 3)
    assert (d["blocks_kept"], d["blocks_total"]) == (1, 4)
    assert d["planning_streak"] == 3


def blocks_of(session):
    from sqlalchemy import select

    from app.modules.day.models import TimeBlock

    return session.scalars(select(TimeBlock).order_by(TimeBlock.start)).all()
