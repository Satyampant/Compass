from datetime import timedelta

import pytest
from sqlalchemy import select

from app.kernel import scheduler
from app.modules.capture import service
from app.modules.learning.models import LearningItem
from app.modules.notify import bot
from app.modules.notify import service as notify
from app.modules.notify.models import Notification
from app.modules.notify.service import Nudge
from tests.fakes import FakeTelegram

ME = 111


@pytest.fixture
def tg(session, fake_clock, monkeypatch):
    fake = FakeTelegram()
    monkeypatch.setattr(notify, "telegram", lambda: fake)
    fake.push_message(ME, "/start")
    bot.poll_once(fake)
    fake.sent.clear()
    return fake


def save_links(session, n):
    for i in range(n):
        service.capture(session, text=f"https://x.com/{i}", channel="web", key=str(i))
    session.commit()


def test_brief_arrives_after_first_run_of_day_3(session, fake_clock, tg):
    save_links(session, 2)
    scheduler.tick()
    assert tg.sent == []  # day 0: nothing to revisit
    fake_clock.advance(days=3, hours=2)
    scheduler.tick()
    scheduler.tick()
    assert len(tg.sent) == 1
    assert tg.sent[0]["text"].startswith("Back on your desk: 2 items")
    assert [b[0] for b in tg.sent[0]["buttons"][0]] == ["1 Book", "1 Let go"]


def test_let_go_in_brief_archives_item(session, fake_clock, tg):
    save_links(session, 1)
    fake_clock.advance(days=3)
    scheduler.tick()
    let_go = tg.sent[0]["buttons"][0][1][1]
    tg.push_tap(ME, let_go)
    bot.poll_once(tg)
    session.expire_all()
    assert session.scalars(select(LearningItem)).one().state == "let_go"


def test_fourth_nudge_is_held_back(session, fake_clock, tg):
    nudges = [Nudge("brief", f"n{i}") for i in range(3)] + [Nudge("last_ask", "ask")]
    rows = notify.send_nudges(session, nudges)
    assert [r.status for r in rows] == ["sent", "sent", "sent", "held"]
    assert tg.texts() == ["ask", "n0", "n1"]
    assert notify.send_nudges(session, [Nudge("brief", "later")])[0].status == "held"
    assert session.scalars(select(Notification).where(Notification.status == "held")).all()


def test_replies_do_not_count(session, fake_clock, tg):
    tg.push_message(ME, "https://a.com")
    bot.poll_once(tg)
    assert len(tg.sent) == 1
    rows = notify.send_nudges(session, [Nudge("brief", f"n{i}") for i in range(3)])
    assert all(r.status == "sent" for r in rows)


def test_last_ask_is_its_own_message(session, fake_clock, tg):
    save_links(session, 1)
    item = session.scalars(select(LearningItem)).one()
    item.captured_at -= timedelta(days=21)
    item.resurface_count, item.next_resurface_at = 3, fake_clock.now()
    session.commit()
    scheduler.tick()
    texts = [t for t in tg.texts() if "Keep it or let it go?" in t]
    assert texts == ["Saved 21 days ago: https://x.com/0. Keep it or let it go?"]
