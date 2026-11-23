"""Export every table as one JSON file, and load such a file into an empty database.

uv run python -m app.modules.system.export load compass-export.json
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import Date, insert, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.kernel import clock, db, migrate
from app.kernel.db import UTCDateTime

FORMAT = 1


def dump(value):
    return value.isoformat() if isinstance(value, date | datetime) else value


def export(session: Session) -> dict:
    """All rows of every table, parents before children."""
    tables = {}
    for table in db.Base.metadata.sorted_tables:
        rows = session.execute(select(table)).mappings()
        tables[table.name] = [{k: dump(v) for k, v in row.items()} for row in rows]
    return {"format": FORMAT, "exported_at": clock.now().isoformat(), "tables": tables}


def parse(column, value):
    if value is None:
        return None
    if isinstance(column.type, UTCDateTime):
        return datetime.fromisoformat(value)
    if isinstance(column.type, Date):
        return date.fromisoformat(value)
    return value


def load(session: Session, data: dict) -> int:
    """Insert an export into an empty database. Returns the number of rows."""
    if data.get("format") != FORMAT:
        raise ValueError(f"unknown export format {data.get('format')}")
    count = 0
    for table in db.Base.metadata.sorted_tables:
        if session.execute(select(table).limit(1)).first() is not None:
            raise ValueError(f"table {table.name} is not empty")
        rows = data["tables"].get(table.name, [])
        if rows:
            cols = table.columns
            session.execute(
                insert(table), [{k: parse(cols[k], v) for k, v in r.items()} for r in rows]
            )
            count += len(rows)
    return count


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "load":
        sys.exit("usage: python -m app.modules.system.export load EXPORT_FILE")
    migrate.upgrade()
    with db.SessionLocal() as s:
        n = load(s, json.loads(Path(sys.argv[2]).read_text()))
        s.commit()
    print(f"Loaded {n} rows into {db.engine.url.database}")
