from datetime import date, timedelta

from app.kernel import clock, db, migrate
from app.modules.autopilot import resurface
from app.modules.capture import service
from app.modules.learning import lifecycle

DAY0 = date(2026, 11, 23)


def save(session, url, key=None):
    return service.capture(session, text=url, channel="web", key=key or url).item


def run_on(session, fake_clock, day):
    """Wake the Mac at 09:00 IST on a given day number and run the morning job."""
    fake_clock.set(fake_clock.start + timedelta(days=day, hours=3))
    resurface.catch_up(session, DAY0 + timedelta(days=day))
    session.flush()
    return [i.title for i in resurface.todays_list(session, DAY0 + timedelta(days=day))]


def test_ignored_item_from_day_0_to_23(session, fake_clock):
    fake_clock.start = fake_clock.now()
    item = save(session, "https://a.com")
    shown = [d for d in range(0, 24) if run_on(session, fake_clock, d)]
    assert shown == [3, 7, 14, 21]
    assert item.state == "expired"


def scenario(tmp_path, fake_clock, name, awake):
    """Save one link a day on days 0..5, waking only on the given days. Lists from day 6 on."""
    db.configure(f"sqlite:///{tmp_path / name}.db")
    migrate.upgrade()
    with db.SessionLocal() as s:
        for n in range(6):
            fake_clock.set(fake_clock.start + timedelta(days=n))
            save(s, f"https://site{n}.com")
            if n in awake:
                run_on(s, fake_clock, n)
        return {d: run_on(s, fake_clock, d) for d in range(6, 12)}


def test_five_days_closed_gives_the_same_list(fake_clock, tmp_path):
    fake_clock.start = fake_clock.now()
    always_on = scenario(tmp_path, fake_clock, "on", awake=range(6))
    asleep = scenario(tmp_path, fake_clock, "asleep", awake={0})
    assert asleep == always_on
    assert always_on[6] == ["https://site3.com"] and always_on[7] == [
        "https://site0.com",
        "https://site4.com",
    ]


def test_list_holds_three_last_asks_first(session, fake_clock):
    fake_clock.start = fake_clock.now()
    for n in range(5):
        save(session, f"https://x.com/{n}")
    old = save(session, "https://old.com")
    old.captured_at = clock.now() - timedelta(days=18)
    old.resurface_count, old.next_resurface_at = 3, clock.now() + timedelta(days=3)
    titles = run_on(session, fake_clock, 3)
    assert titles == ["https://old.com", "https://x.com/0", "https://x.com/1"]
    assert run_on(session, fake_clock, 4) == [
        "https://x.com/2",
        "https://x.com/3",
        "https://x.com/4",
    ]


def test_duplicate_goes_to_top(session, fake_clock):
    fake_clock.start = fake_clock.now()
    for n in range(3):
        save(session, f"https://x.com/{n}")
    run_on(session, fake_clock, 3)
    save(session, "https://x.com/2", key="again")
    assert resurface.todays_list(session, DAY0 + timedelta(days=3))[0].url == "https://x.com/2"


def test_decided_item_leaves_the_list(session, fake_clock):
    fake_clock.start = fake_clock.now()
    item = save(session, "https://a.com")
    assert run_on(session, fake_clock, 3) == ["https://a.com"]
    lifecycle.transition(session, item, "let_go")
    assert run_on(session, fake_clock, 7) == []
