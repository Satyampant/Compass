from datetime import timedelta

import pytest
from sqlalchemy import select

from app.kernel import clock, jobs, scheduler
from app.kernel.models import Job


@pytest.fixture
def runs(session, fake_clock):
    """Count morning_run executions with a stub handler."""
    calls = []
    original = jobs.HANDLERS.get("morning_run")
    jobs.HANDLERS["morning_run"] = lambda s, payload: calls.append(clock.now())
    yield calls
    if original:
        jobs.HANDLERS["morning_run"] = original
    else:
        jobs.HANDLERS.pop("morning_run")


def test_job_due_at_six_runs_once_when_clock_jumps_to_nine(session, fake_clock, runs):
    fake_clock.advance(minutes=-60)  # 05:00 IST: only yesterday's run is owed
    scheduler.tick()
    assert len(runs) == 1
    runs.clear()
    fake_clock.advance(hours=4)  # 09:00 IST
    scheduler.tick()
    scheduler.tick()
    assert runs == [fake_clock.now()]


def test_long_sleep_gives_one_run(session, fake_clock, runs):
    scheduler.tick()
    runs.clear()
    fake_clock.advance(days=5, hours=3)
    scheduler.tick()
    assert len(runs) == 1


def test_crash_mid_job_runs_once_after_restart(session, fake_clock, runs):
    with scheduler.db.SessionLocal() as s:
        scheduler.ensure_daily(s, fake_clock.now())
        claimed = 0
        while jobs.claim(s, fake_clock.now()):  # every due job claimed, then the process dies
            claimed += 1
        assert claimed == len(scheduler.DAILY) + len(scheduler.INTERVALS)
        s.commit()
    assert scheduler.tick() == 0
    scheduler.startup()
    scheduler.tick()
    scheduler.tick()
    assert len(runs) == 1


def test_failing_job_retries_then_gives_up(session, fake_clock):
    def boom(s, payload):
        raise RuntimeError("boom")

    jobs.HANDLERS["boom"] = boom
    jobs.enqueue(session, "boom", fake_clock.now())
    session.commit()
    for _ in range(jobs.MAX_ATTEMPTS):
        scheduler.run_one(fake_clock.now())
        fake_clock.advance(hours=1)
    job = session.scalars(select(Job).where(Job.kind == "boom")).one()
    session.refresh(job)
    assert job.status == "failed" and job.attempts == jobs.MAX_ATTEMPTS
    assert not scheduler.run_one(fake_clock.now() + timedelta(days=1))
    jobs.HANDLERS.pop("boom")
