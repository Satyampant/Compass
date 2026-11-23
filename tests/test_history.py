from datetime import UTC, date, datetime, timedelta

from app.kernel.models import Event
from app.modules.day.models import DailyLog


def test_history_matches_daily_logs_and_events(client, session, fake_clock):
    session.add(
        DailyLog(
            day=date(2026, 11, 20),
            planned_at=datetime(2026, 11, 19, 15, tzinfo=UTC),
            closed_at=datetime(2026, 11, 20, 14, tzinfo=UTC),
        )
    )
    session.add(DailyLog(day=date(2026, 11, 21), planned_at=datetime(2026, 11, 21, 6, tzinfo=UTC)))
    session.add(DailyLog(day=date(2026, 9, 1), closed_at=datetime(2026, 9, 1, 14, tzinfo=UTC)))
    at = lambda d: datetime(2026, 11, d, 6, tzinfo=UTC)  # noqa: E731
    for d, kind in [
        (17, "item.captured"),
        (18, "item.captured"),
        (19, "item.let_go"),
        (24, "item.captured"),
        (25, "item.finish"),
        (25, "item.expire"),
        (25, "item.book"),
    ]:
        session.add(Event(at=at(d), kind=kind, entity="learning_item", entity_id=1, data={}))
    session.commit()
    h = client.get("/v1/reviews/history").json()
    assert len(h["days"]) == 84 and h["days"][0]["date"] == "2026-09-07"
    assert h["days"][-1]["date"] == "2026-11-29"
    marks = {d["date"]: (d["planned"], d["closed"]) for d in h["days"]}
    assert marks["2026-11-20"] == (True, True)
    assert marks["2026-11-21"] == (False, False)  # planned at 11:30 on the day: too late
    assert "2026-09-01" not in marks
    weeks = {w["week_start"]: (w["added"], w["closed"]) for w in h["weeks"]}
    assert len(weeks) == 8
    assert weeks["2026-11-16"] == (2, 1) and weeks["2026-11-23"] == (1, 2)
    assert date.fromisoformat(h["weeks"][0]["week_start"]) == date(2026, 11, 23) - timedelta(
        weeks=7
    )
