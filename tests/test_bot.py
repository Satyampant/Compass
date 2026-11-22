import pytest

from app.kernel import settings
from app.modules.notify import bot
from tests.fakes import FakeTelegram

ME, STRANGER = 111, 999


@pytest.fixture
def tg(session):
    return FakeTelegram()


def test_first_start_locks_the_chat(session, tg):
    tg.push_message(ME, "/start")
    bot.poll_once(tg)
    session.expire_all()
    assert settings.get(session, bot.CHAT_KEY) == ME
    assert "connected" in tg.texts()[0]


def test_bot_ignores_a_second_account(session, tg):
    tg.push_message(ME, "/start")
    tg.push_message(STRANGER, "/start")
    tg.push_message(STRANGER, "https://evil.example.com")
    bot.poll_once(tg)
    assert [m["chat_id"] for m in tg.sent] == [ME]
    session.expire_all()
    assert settings.get(session, bot.CHAT_KEY) == ME


def test_button_tap_reaches_handler(session, tg):
    seen = []
    bot.CALLBACKS["ping"] = lambda s, ctx, args: (seen.append(args), ctx.answer("pong"))
    tg.push_message(ME, "/start")
    tg.push_tap(ME, "ping:a:7")
    tg.push_tap(STRANGER, "ping:b:8")
    bot.poll_once(tg)
    assert seen == [["a", "7"]]
    assert tg.answers == [("cb101", "pong")]
    bot.CALLBACKS.pop("ping")


def test_processed_updates_are_confirmed(session, tg):
    tg.push_message(ME, "/start")
    assert bot.poll_once(tg) == 1
    assert bot.poll_once(tg) == 0
