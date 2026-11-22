"""PRD 'accepted when' checks for phase 0, in the PRD's words.

Checks that need the phone, the lid or a restart are in docs/acceptance-p0.md.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.kernel import scheduler
from app.modules.autopilot import brief, resurface
from app.modules.capture import service
from app.modules.learning.models import LearningItem
from app.modules.notify import bot
from app.modules.notify import service as notify
from app.modules.notify.service import Nudge
from tests.fakes import FakeTelegram

ME = 111
MONDAY = date(2026, 11, 23)


@pytest.fixture
def tg(session, fake_clock, monkeypatch):
    fake = FakeTelegram()
    monkeypatch.setattr(notify, "telegram", lambda: fake)
    fake.push_message(ME, "/start")
    bot.poll_once(fake)
    fake.sent.clear()
    return fake


def on_day(session, fake_clock, n):
    fake_clock.set(fake_clock.start + timedelta(days=n, hours=3))
    resurface.catch_up(session, MONDAY + timedelta(days=n))
    session.commit()
    return [i.url for i in resurface.revisit_list(session)]


def test_cap_sharing_the_same_link_twice_leaves_one_card(client, fake_clock):
    client.post("/v1/captures", json={"text": "https://raft.github.io"})
    client.post("/v1/captures", json={"text": "https://raft.github.io/?utm_source=tg"})
    assert len(client.get("/v1/learning-items?state=inbox").json()) == 1


def test_cap_links_shared_while_closed_arrive_with_saved(session, tg):
    for n in range(3):
        tg.push_message(ME, f"https://site{n}.com", date=1795400000 + n)
    bot.poll_once(tg)
    assert all(t.startswith("Saved") for t in tg.texts()) and len(tg.texts()) == 3


def test_lq_a_let_go_item_never_appears_again(client, session, fake_clock, tg):
    fake_clock.start = fake_clock.now()
    item_id = client.post("/v1/captures", json={"text": "https://gone.com"}).json()["item_id"]
    client.post(f"/v1/learning-items/{item_id}/transitions", json={"action": "let_go"})
    for n in range(0, 30):
        assert "https://gone.com" not in on_day(session, fake_clock, n)
        assert not brief.build(session)
    assert client.get("/v1/learning-items?state=inbox,booked,learning").json() == []


def test_ap_link_saved_monday_appears_thursday_without_action(session, fake_clock):
    fake_clock.start = fake_clock.now()
    service.capture(session, text="https://raft.github.io", channel="telegram", key="1")
    session.commit()
    assert on_day(session, fake_clock, 2) == []
    assert on_day(session, fake_clock, 3) == ["https://raft.github.io"]


def test_nu_let_go_in_morning_brief_shows_on_next_web_load(client, session, fake_clock, tg):
    client.post("/v1/captures", json={"text": "https://a.com"})
    fake_clock.advance(days=3)
    scheduler.tick()
    scheduler.tick()
    tg.push_tap(ME, tg.sent[0]["buttons"][0][1][1])
    bot.poll_once(tg)
    assert client.get("/v1/today").json()["revisit"] == []
    session.expire_all()
    assert session.scalars(select(LearningItem)).one().state == "let_go"


def test_nu_five_possible_nudges_send_three_by_priority(session, tg):
    nudges = [
        Nudge("brief", "brief"),
        Nudge("other", "other"),
        Nudge("block_reminder", "block"),
        Nudge("last_ask", "ask 1"),
        Nudge("last_ask", "ask 2"),
    ]
    notify.send_nudges(session, nudges)
    assert tg.texts() == ["ask 1", "ask 2", "block"]
