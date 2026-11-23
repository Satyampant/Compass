from datetime import date, timedelta

import httpx
from playwright.sync_api import expect

from e2e.conftest import shot
from e2e.test_web import settle

MONDAY = date.today() - timedelta(days=date.today().weekday())


def add(server, title, minutes, offset):
    day = (MONDAY + timedelta(days=offset)).isoformat()
    r = httpx.post(
        f"{server}/v1/tasks", json={"title": title, "estimate_min": minutes, "planned_date": day}
    )
    assert r.status_code == 201


def drag(page, source, target):
    box = source.bounding_box()
    dest = target.bounding_box()
    page.mouse.move(box["x"] + 20, box["y"] + 10)
    page.mouse.down()
    page.mouse.move(box["x"] + 40, box["y"] + 20, steps=4)
    page.mouse.move(dest["x"] + dest["width"] / 2, dest["y"] + 60, steps=12)
    page.mouse.up()
    settle(page)


def hours(page, offset):
    return page.get_by_test_id(f"hours-{(MONDAY + timedelta(days=offset)).isoformat()}")


def test_drag_updates_both_days_and_overbooked_week_warns(page, server):
    add(server, "Split parity", 180, 0)
    add(server, "Metrics pack", 60, 3)
    page.goto(page.url.split("#")[0] + "#week")
    expect(hours(page, 0)).to_have_text("3h")
    expect(hours(page, 3)).to_have_text("1h")

    card = page.locator(".kcard", has_text="Split parity")
    drag(page, card, page.locator(".board.week section.col").nth(3))
    expect(hours(page, 0)).to_have_text("0h")
    expect(hours(page, 3)).to_have_text("4h")
    expect(page.get_by_test_id("week-total")).to_have_class("chip good")

    for offset in range(4):
        add(server, "Deep work", 10 * 60, offset)
    page.reload()
    expect(page.get_by_test_id("week-total")).to_contain_text("44h planned · 40h capacity")
    expect(page.get_by_test_id("week-total")).to_have_class("chip warn")
    expect(hours(page, 3)).to_have_class("aging")
    shot(page, "week")
