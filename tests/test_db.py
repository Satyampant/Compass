from datetime import UTC, date, datetime

from sqlalchemy import select, text

from app.models import Capture, DailyLog, Event, Job, LearningItem, Note, Setting, Task

NOW = datetime(2026, 11, 23, 4, 30, tzinfo=UTC)


def test_wal_mode(session):
    assert session.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_write_and_read_each_table(session):
    item = LearningItem(title="Raft", url="https://raft.github.io", captured_at=NOW)
    task = Task(title="Investor call", planned_date=date(2026, 11, 23), created_at=NOW)
    note = Note(body="idea", created_at=NOW)
    session.add_all([item, task, note])
    session.flush()
    session.add_all(
        [
            Capture(idempotency_key="k1", channel="web", text="x", created_at=NOW, item_id=item.id),
            Event(at=NOW, kind="item.captured", entity="learning_item", entity_id=item.id),
            Job(kind="morning_run", run_at=NOW),
            Setting(key="nudges_per_day", value=3),
            DailyLog(day=date(2026, 11, 23), closed_at=NOW),
        ]
    )
    session.commit()
    session.expunge_all()

    for model in (Capture, DailyLog, Event, Job, LearningItem, Note, Setting, Task):
        assert session.scalars(select(model)).one()
    assert session.scalars(select(LearningItem)).one().captured_at == NOW
