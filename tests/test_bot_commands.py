from datetime import date, timedelta

from app.kernel import clock
from app.modules.autopilot import brief
from app.modules.capture import service as capture
from app.modules.day import service as day
from app.modules.learning import lifecycle
from app.modules.notify import bot
from tests.test_brief import ME, tg  # noqa: F401
from tests.test_resurface import run_on

DAY = date(2026, 11, 23)


def ask(session, tg, text):  # noqa: F811
    tg.sent.clear()
    tg.push_message(ME, text)
    bot.poll_once(tg)
    session.expire_all()
    return tg.sent[-1]


def ranked(session):
    a = day.create_task(session, "Split parity", DAY, 180)
    b = day.create_task(session, "Investor call", DAY, 60)
    day.create_task(session, "Gym", DAY, 45)
    day.set_top(session, DAY, [a.id, b.id])
    a.done_at = clock.now()
    session.commit()


def test_today_lists_top_three_and_next_block(session, tg):  # noqa: F811
    assert ask(session, tg, "/today")["text"] == (
        "No top three yet.\n\nNext block: Mon 16:00 · nothing booked yet"
    )
    ranked(session)
    item = capture.capture(session, text="https://k8s.io/svc", channel="web", key="k").item
    lifecycle.transition(session, item, "book", booked_for=clock.now() + timedelta(days=2))
    session.commit()
    assert ask(session, tg, "/today")["text"] == (
        "Today's top three\n"
        "1. Split parity · 180 min (done)\n"
        "2. Investor call · 60 min\n\n"
        "Next block: Wed 06:00 · https://k8s.io/svc"
    )


def test_queue_lists_inbox_and_revisit(session, fake_clock, tg):  # noqa: F811
    fake_clock.start = fake_clock.now()
    assert (
        ask(session, tg, "/queue")["text"] == "Inbox: 0 waiting\nNothing back on your desk today."
    )
    for n in range(2):
        capture.capture(session, text=f"https://x.com/{n}", channel="web", key=str(n))
    run_on(session, fake_clock, 3)
    session.commit()
    sent = ask(session, tg, "/queue")
    assert sent["text"].splitlines() == [
        "Inbox: 2 waiting",
        "Back on your desk: 2 items",
        "1. https://x.com/0 · 20 min",
        "2. https://x.com/1 · 20 min",
    ]
    assert sent["buttons"][0][0][1].startswith("item:book:")


def test_unknown_command_lists_commands(session, tg):  # noqa: F811
    assert ask(session, tg, "/help")["text"] == "Commands: /queue, /today"
    assert ask(session, tg, "/today@Compass420Bot")["text"].startswith("No top three")


def test_brief_leads_with_top_three(session, fake_clock, tg):  # noqa: F811
    ranked(session)
    nudges = brief.build(session)
    assert nudges[0].kind == "brief"
    assert nudges[0].text.splitlines()[:3] == [
        "Today's top three",
        "1. Split parity · 180 min (done)",
        "2. Investor call · 60 min",
    ]
