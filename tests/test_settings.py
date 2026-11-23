from datetime import timedelta

from sqlalchemy import select

from app.modules.autopilot import cycle
from app.modules.day.models import TimeBlock
from app.modules.learning.models import LearningItem
from tests.test_fill import save
from tests.test_protect import ist


def slots(session):
    return session.scalars(
        select(TimeBlock)
        .where(TimeBlock.protected.is_(True), TimeBlock.sync != "delete")
        .order_by(TimeBlock.start)
    ).all()


def test_changing_slot_times_regenerates_next_weeks_slots(client, session, fake_clock, calendar):
    item = save(session, "https://a.com")
    cycle.run(session)
    session.commit()
    assert slots(session)[0].item_id == item.id
    new = [{"weekday": 1, "time": "07:00"}, {"weekday": 3, "time": "18:30"}]
    r = client.put("/v1/settings", json={"learning_slots": new, "learning_block_min": 60})
    assert r.status_code == 200 and r.json()["learning_slots"] == new
    session.expire_all()
    starts = [s.start for s in slots(session)]
    assert starts == [
        ist(24, "07:00"),
        ist(26, "18:30"),
        ist(24, "07:00") + timedelta(days=7),
        ist(26, "18:30") + timedelta(days=7),
    ]
    assert all(s.end - s.start == timedelta(minutes=60) for s in slots(session))
    moved = session.get(LearningItem, item.id)
    assert moved.state == "booked" and moved.booked_for == ist(24, "07:00")
    removed = [w for w in calendar.writes if w[0] == "delete"]
    assert len(removed) == 8


def test_bad_values_are_refused_and_nothing_is_stored(client, fake_clock):
    for body, message in [
        ({"resurface_days": [7, 3]}, "days must rise"),
        ({"learning_slots": [{"weekday": 9, "time": "16:00"}]}, "weekday"),
        ({"morning_run_time": "6am"}, "time like 16:00"),
        ({"timezone": "Mars/Olympus"}, "time zone"),
        ({"day_window": ["20:00", "08:00"]}, "end after it starts"),
        ({"nudges_per_day": "3"}, "whole number"),
        ({"colour": "green"}, "unknown setting"),
        ({"pace_on_track_points": 30}, "must not exceed"),
    ]:
        r = client.put("/v1/settings", json={"top_priorities": 5, **body})
        assert r.status_code == 422 and message in r.json()["detail"], body
    assert client.get("/v1/settings").json()["top_priorities"] == 3


def test_settings_change_the_rules(client, fake_clock):
    client.put("/v1/settings", json={"top_priorities": 5, "capacity_week_hours": 30})
    assert client.get("/v1/today").json()["top_limit"] == 5
    assert client.get("/v1/week").json()["capacity_min"] == 30 * 60


def test_settings_are_kept_when_the_calendar_is_not_connected(client, fake_clock):
    r = client.put("/v1/settings", json={"learning_block_min": 60, "top_priorities": 4})
    assert r.status_code == 200
    values = client.get("/v1/settings").json()
    assert (values["learning_block_min"], values["top_priorities"]) == (60, 4)
