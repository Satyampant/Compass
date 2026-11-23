from app.kernel import jobs, scheduler
from app.kernel.models import Job
from tests.test_protect import ist


def rows(client):
    return {r["name"]: r for r in client.get("/v1/status").json()["rows"]}


def test_stopping_the_backup_for_a_day_turns_its_row_to_a_warning(client, session, fake_clock):
    assert rows(client)["Backup"]["ok"] is False  # nothing yet
    scheduler.tick()
    r = rows(client)
    assert r["Backup"]["ok"] and r["Backup"]["detail"].startswith("compass-2026-11-23.db")
    assert r["Morning run"]["ok"] and r["Day rollup"]["ok"]
    jobs.HANDLERS["daily_backup"], real = (lambda s, p: None), jobs.HANDLERS["daily_backup"]
    try:
        fake_clock.advance(days=1, hours=3)
        scheduler.tick()
    finally:
        jobs.HANDLERS["daily_backup"] = real
    r = rows(client)
    assert r["Backup"]["ok"] is True  # yesterday's copy still counts
    fake_clock.advance(days=1)
    r = rows(client)
    assert r["Backup"]["ok"] is False and r["Backup"]["detail"].startswith("compass-2026-11-23")


def test_failed_jobs_and_telegram_check(client, session, fake_clock):
    session.add(
        Job(
            kind="enrich_item",
            run_at=ist(23, "06:00"),
            status="failed",
            attempts=5,
            finished_at=ist(23, "06:30"),
            last_error="RuntimeError('boom')",
        )
    )
    session.commit()
    s = client.get("/v1/status").json()
    assert s["failures"][0]["kind"] == "enrich_item" and "boom" in s["failures"][0]["error"]
    names = {r["name"]: r for r in s["rows"]}
    assert names["Telegram check"]["ok"] is False and names["Calendar sync"]["ok"] is False
