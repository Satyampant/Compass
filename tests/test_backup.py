import sqlite3
from datetime import date, timedelta
from pathlib import Path

from app.kernel import backup, db, scheduler, settings
from app.modules.day.service import create_task

REAL_DIR = backup.backup_dir  # taken before the autouse fixture replaces it


def test_daily_backup_runs_once_and_restores(session, fake_clock, tmp_path):
    create_task(session, "Split parity", date(2026, 11, 23))
    session.commit()
    scheduler.tick()
    folder = tmp_path / "backups"
    assert [p.name for p in folder.iterdir()] == ["compass-2026-11-23.db"]

    restored = backup.restore(folder / "compass-2026-11-23.db", tmp_path / "scratch")
    with sqlite3.connect(restored) as con:
        assert con.execute("select title from tasks").fetchall() == [("Split parity",)]
        assert con.execute("pragma integrity_check").fetchone() == ("ok",)
    con.close()


def test_keeps_the_newest_thirty(session, tmp_path):
    folder = tmp_path / "backups"
    folder.mkdir()
    start = date(2026, 10, 1)
    for n in range(32):
        (folder / f"compass-{start + timedelta(days=n)}.db").write_text("x")
    gone = backup.prune(folder)
    assert [p.name for p in gone] == ["compass-2026-10-01.db", "compass-2026-10-02.db"]
    assert len(list(folder.glob("*.db"))) == 30


def test_backup_dir_setting(session):
    assert REAL_DIR(session) == db.ROOT / "data" / "backups"
    settings.put(session, "backup_dir", "~/Drive/Compass")
    assert REAL_DIR(session) == Path.home() / "Drive" / "Compass"
