"""Daily copy of the database with SQLite's online backup, keeping the newest 30.

Restore a copy into a scratch folder and open the app on it:

    uv run python -m app.kernel.backup restore BACKUP_FILE SCRATCH_DIR

Point backups at the Google Drive folder:

    uv run python -m app.kernel.backup set-dir "~/.../My Drive/Compass"
"""

import logging
import sqlite3
import sys
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.kernel import db, jobs, settings

log = logging.getLogger(__name__)

KEEP = 30
PREFIX = "compass-"


def backup_dir(session: Session) -> Path:
    """Where copies go: the backup_dir setting, or data/backups inside the project."""
    configured = settings.get(session, "backup_dir")
    return Path(configured).expanduser() if configured else db.ROOT / "data" / "backups"


def copy(source: sqlite3.Connection, target: Path) -> Path:
    """Write a consistent copy of an open database to target."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".partial")
    with sqlite3.connect(partial) as out:
        source.backup(out)
    out.close()
    partial.replace(target)
    return target


def prune(folder: Path, keep: int = KEEP) -> list[Path]:
    """Delete all but the newest `keep` copies. Names sort by date."""
    copies = sorted(folder.glob(f"{PREFIX}*.db"))
    old = copies[:-keep] if len(copies) > keep else []
    for path in old:
        path.unlink()
    return old


def make_backup(session: Session, day: date) -> Path:
    """Copy the live database to the backup folder as compass-YYYY-MM-DD.db, then prune."""
    folder = backup_dir(session)
    raw = db.engine.raw_connection()
    try:
        path = copy(raw.driver_connection, folder / f"{PREFIX}{day.isoformat()}.db")
    finally:
        raw.close()
    prune(folder)
    log.info("backup written to %s", path)
    return path


@jobs.handler("daily_backup")
def daily_backup(session: Session, payload: dict) -> None:
    """Job: today's copy."""
    make_backup(session, settings.today(session))


def restore(backup: Path, scratch: Path) -> Path:
    """Copy a backup into scratch/compass.db, ready to open the app on."""
    with sqlite3.connect(backup) as src:
        target = copy(src, scratch / "compass.db")
    src.close()
    return target


def set_dir(path: str) -> None:
    """Store the backup folder setting."""
    with db.SessionLocal() as s:
        settings.put(s, "backup_dir", path)
        s.commit()


USAGE = "usage: python -m app.kernel.backup restore BACKUP_FILE SCRATCH_DIR | set-dir PATH"

if __name__ == "__main__":
    if sys.argv[1:2] == ["set-dir"] and len(sys.argv) == 3:
        set_dir(sys.argv[2])
        sys.exit(f"Backups will go to {sys.argv[2]}")
    if len(sys.argv) != 4 or sys.argv[1] != "restore":
        sys.exit(USAGE)
    target = restore(Path(sys.argv[2]), Path(sys.argv[3]))
    print(f"Restored to {target}. Open the app on it with:")
    print(f"  COMPASS_DB_URL=sqlite:///{target} COMPASS_BACKGROUND=0 \\")
    print("  uv run uvicorn app.main:app --port 8002")
