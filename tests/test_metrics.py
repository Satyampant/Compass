from datetime import UTC, date, datetime, timedelta

from app.modules.autopilot import booking
from app.modules.capture import service as capture
from app.modules.day import blocks
from app.modules.day.models import DailyLog
from app.modules.day.service import create_task, set_top
from app.modules.learning import lifecycle
from app.modules.review import metrics
from tests.test_goal_links import tree
from tests.test_protect import ist

D = date(2026, 11, 23)


def test_pure_functions_match_hand_worked_examples():
    # 180 + 60 + 45 tied of 375 minutes = 285 / 375
    assert metrics.alignment([(180, True), (60, True), (90, False), (45, True)]) == 0.76
    assert metrics.alignment([]) is None
    assert metrics.top_three([True, False, True]) == 2 / 3
    assert metrics.blocks_kept(["kept", "missed", "started", "planned"]) == (2, 4)
    days = {D - timedelta(days=n) for n in range(4)} | {D - timedelta(days=6)}
    assert metrics.streak(days, D) == 4
    assert metrics.streak(days, D + timedelta(days=1)) == 4  # today not counted yet
    assert metrics.streak(days, D + timedelta(days=2)) == 0


def test_day_alignment_from_blocks(session, fake_clock):
    year, quarter, week = tree(session)
    tied = create_task(session, "Split parity", D, 180, goal_id=week.id)
    loose = create_task(session, "Inbox zero", D, 60)
    item = capture.capture(
        session, text="https://k8s.io", channel="web", key="k", goal_id=quarter.id
    ).item
    blocks.create(session, "task", ist(23, "09:00"), ist(23, "12:00"), "Parity", task_id=tied.id)
    blocks.create(session, "task", ist(23, "12:00"), ist(23, "13:00"), "Inbox", task_id=loose.id)
    blocks.create(session, "learning", ist(23, "16:00"), ist(23, "16:45"), "K8s", item_id=item.id)
    blocks.create(session, "learning", ist(23, "18:00"), ist(23, "18:45"), "empty slot")
    blocks.create(session, "meeting", ist(23, "07:00"), ist(23, "09:00"), "Early call")
    numbers = metrics.day_numbers(session, D)
    # Meeting clipped to 08:00-09:00 is 60 untied minutes. 180 + 45 tied of 345.
    assert (numbers.aligned_min, numbers.planned_min) == (225, 345)
    assert round(numbers.alignment, 3) == 0.652


def test_day_alignment_from_tasks_without_blocks(session, fake_clock):
    year, quarter, week = tree(session)
    a = create_task(session, "a", D, 90, goal_id=week.id)
    b = create_task(session, "b", D, 30)
    create_task(session, "c", D, 60).dropped_at = fake_clock.now()
    set_top(session, D, [a.id, b.id])
    a.done_at = fake_clock.now()
    numbers = metrics.day_numbers(session, D)
    assert (numbers.aligned_min, numbers.planned_min) == (90, 120)
    assert (numbers.top_planned, numbers.top_done) == (2, 1)


def test_queue_flow_and_kept_blocks(session, fake_clock):
    for n in range(5):
        capture.capture(session, text=f"https://x{n}.com", channel="web", key=str(n))
    items = list(session.scalars(metrics.select(metrics.LearningItem)))
    lifecycle.transition(session, items[0], "let_go")
    booking.move(session, items[1], "book")
    booking.move(session, items[1], "start")
    booking.move(session, items[1], "finish", note="done")
    assert metrics.queue_flow(session, D, D) == (5, 2)
    assert metrics.queue_flow(session, D + timedelta(days=1), D + timedelta(days=7)) == (0, 0)
    assert metrics.blocks_kept(metrics.week_slots(session, D)) == (1, 1)


def test_planning_and_shutdown_streaks(session, fake_clock):
    evening = lambda d: datetime(2026, 11, d - 1, 15, 0, tzinfo=UTC)  # noqa: E731  20:30 IST before
    for d in (20, 21, 22):
        session.add(
            DailyLog(day=date(2026, 11, d), planned_at=evening(d), closed_at=evening(d + 1))
        )
    late = datetime(2026, 11, 23, 5, 0, tzinfo=UTC)  # 10:30 IST on the day itself
    session.add(DailyLog(day=D, planned_at=late))
    session.flush()
    assert metrics.streak(metrics.planned_days(session), D) == 3
    assert metrics.streak(metrics.closed_days(session), D) == 3
