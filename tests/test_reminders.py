from datetime import timedelta

import pytest

from app.kernel import scheduler
from app.modules.autopilot import cycle
from app.modules.capture import service as capture
from app.modules.notify import bot
from app.modules.notify import service as notify
from tests.fakes import FakeTelegram
from tests.test_fill import slots
from tests.test_protect import ist, meeting

ME = 111


@pytest.fixture
def tg(session, fake_clock, monkeypatch):
    fake = FakeTelegram()
    monkeypatch.setattr(notify, "telegram", lambda: fake)
    fake.push_message(ME, "/start")
    bot.poll_once(fake)
    fake.sent.clear()
    return fake


def run_until_idle(session):
    session.commit()
    while scheduler.run_one(scheduler.clock.now()):
        pass
    session.expire_all()


def at(session, fake_clock, when):
    fake_clock.set(when)
    with scheduler.db.SessionLocal() as s:
        scheduler.ensure_daily(s, when)
        s.commit()
    run_until_idle(session)


def booked(session, url="https://k8s.io/services"):
    item = capture.capture(session, text=url, channel="web", key=url).item
    item.title = "K8s Services"
    cycle.run(session)
    session.commit()
    return item


def test_reminder_fifteen_minutes_before_with_title_and_link(session, fake_clock, tg, calendar):
    booked(session)
    monday = slots(session)[0]
    at(session, fake_clock, monday.start - timedelta(minutes=16))
    assert [m["text"] for m in tg.sent if "Learning block" in m["text"]] == []
    at(session, fake_clock, monday.start - timedelta(minutes=15))
    texts = [m["text"] for m in tg.sent if "Learning block" in m["text"]]
    assert texts == ["Learning block at Mon 16:00: K8s Services\nhttps://k8s.io/services"]


def test_moved_block_reminds_at_its_new_time_only(session, fake_clock, tg, calendar):
    booked(session)
    calendar.put("primary", meeting("Call", 23, "16:00", "16:30"))
    cycle.run(session)
    session.commit()
    at(session, fake_clock, ist(23, "15:45"))
    at(session, fake_clock, ist(23, "16:15"))
    texts = [m["text"] for m in tg.sent if "Learning block" in m["text"]]
    assert texts == ["Learning block at Mon 16:30: K8s Services\nhttps://k8s.io/services"]


def test_shutdown_nudge_at_1930_unless_closed(client, session, fake_clock, tg):
    at(session, fake_clock, ist(23, "19:31"))
    assert [m["text"] for m in tg.sent][-1].startswith("Time to close the day")
    tg.sent.clear()
    client.post("/v1/days/2026-11-24/shutdown", json={"learned_line": "x"})
    at(session, fake_clock, ist(24, "19:31"))
    assert tg.sent == []


def test_two_day_sleep_gives_one_message(session, fake_clock, tg, calendar):
    for n in range(3):
        booked(session, f"https://site{n}.example.com")
    for n in range(4):
        capture.capture(session, text=f"https://old{n}.example.com", channel="web", key=f"o{n}")
    session.commit()
    at(session, fake_clock, ist(23, "06:30"))
    tg.sent.clear()
    # The lid closes on Monday morning and opens on Wednesday at 09:00.
    at(session, fake_clock, ist(25, "09:00"))
    assert len(tg.sent) == 1
    assert tg.sent[0]["text"].startswith("Back on your desk")
