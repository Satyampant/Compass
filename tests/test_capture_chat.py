import pytest
from sqlalchemy import select

from app.modules.capture import service
from app.modules.learning.models import LearningItem
from app.modules.notify import bot
from tests.fakes import FakeTelegram

ME = 111
DAY = 86400


@pytest.fixture
def tg(session, fake_clock):
    fake = FakeTelegram()
    fake.push_message(ME, "/start")
    bot.poll_once(fake)
    fake.sent.clear()
    return fake


def items(session):
    session.expire_all()
    return session.scalars(select(LearningItem).order_by(LearningItem.id)).all()


def test_three_links_shared_while_stopped_arrive_in_order(session, tg):
    for n, url in enumerate(["https://a.com/1", "https://b.com/2", "https://c.com/3"]):
        tg.push_message(ME, url, date=1795400000 + n)
    bot.poll_once(tg)
    assert [i.url for i in items(session)] == [
        "https://a.com/1",
        "https://b.com/2",
        "https://c.com/3",
    ]
    assert [t.split(" · ")[0] for t in tg.texts()] == ["Saved"] * 3


def test_duplicate_gets_already_saved_with_buttons(session, tg):
    tg.push_message(ME, "https://raft.github.io", date=1795400000)
    tg.push_message(ME, "https://raft.github.io/", date=1795400000 + 9 * DAY)
    bot.poll_once(tg)
    assert len(items(session)) == 1
    assert tg.sent[1]["text"] == "Already saved 9 days ago. It is now top of today's list."
    assert [b[0] for b in tg.sent[1]["buttons"][0]] == ["Book", "Let go"]


def test_plain_text_gets_three_buttons_then_resolves(session, tg):
    tg.push_message(ME, "Look into CRDTs")
    bot.poll_once(tg)
    buttons = tg.sent[0]["buttons"][0]
    assert [b[0] for b in buttons] == ["Learn later", "Task", "Note"]
    tg.push_tap(ME, buttons[1][1])
    bot.poll_once(tg)
    assert tg.edits[0]["text"].startswith("Saved as a task for today")


def test_let_go_and_book_buttons(session, tg):
    tg.push_message(ME, "https://a.com")
    tg.push_message(ME, "https://b.com")
    bot.poll_once(tg)
    a, b = items(session)
    tg.push_tap(ME, f"item:let_go:{a.id}")
    tg.push_tap(ME, f"item:book:{b.id}")
    tg.push_tap(ME, f"item:book:{a.id}")
    bot.poll_once(tg)
    a, b = items(session)
    assert a.state == "let_go" and b.state == "booked"
    assert tg.edits[1]["text"].startswith("Booked for Mon 16:00")
    assert tg.answers[-1][1] == "Already let go"


def test_failed_store_is_not_confirmed_and_arrives_again(session, tg, monkeypatch):
    real = service.capture
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("disk full")
        return real(*args, **kwargs)

    monkeypatch.setattr(service, "capture", flaky)
    tg.push_message(ME, "https://a.com")
    with pytest.raises(RuntimeError):
        bot.poll_once(tg)
    assert items(session) == [] and tg.sent == []
    bot.poll_once(tg)
    assert len(items(session)) == 1 and tg.texts()[0].startswith("Saved")
