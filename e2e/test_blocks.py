import re
from datetime import date, datetime, time

import httpx
from playwright.sync_api import expect

from e2e.conftest import INFLIGHT, shot

NOW = re.compile(r"\bnow\b")


def local(hour, minute=0):
    return datetime.combine(date.today(), time(hour, minute)).astimezone()


def test_banner_and_highlight_that_moves(browser, server):
    item = httpx.post(f"{server}/v1/captures", json={"text": "https://k8s.io/services"}).json()
    r = httpx.post(
        f"{server}/v1/learning-items/{item['item_id']}/transitions",
        json={"action": "book", "booked_for": local(10).isoformat()},
    )
    assert r.status_code == 200
    context = browser.new_context(viewport={"width": 1360, "height": 900})
    context.add_init_script(INFLIGHT)
    page = context.new_page()
    page.clock.install(time=local(10, 10))
    page.goto(server)
    expect(page.locator(".calendar-banner")).to_contain_text("Calendar not connected")
    slot = page.locator(".slot", has_text="Learning: https://k8s.io/services")
    expect(slot).to_have_class(NOW)
    expect(slot.locator(".chip")).to_have_text("Now")
    shot(page, "today-blocks")
    page.clock.run_for("01:00:00")
    expect(slot).not_to_have_class(NOW)
    expect(
        page.locator(".mark", has_text="NSE opens").or_(page.locator(".slot"))
    ).not_to_have_count(0)
    context.close()


def test_direction_check_card(page, server):
    page.get_by_label("New task").fill("Split parity")
    page.get_by_role("button", name="Add", exact=True).click()
    expect(page.get_by_test_id("alignment")).to_have_text("0%")
    expect(page.locator(".fact", has_text="Days planned in a row")).to_contain_text("0")
    shot(page, "today-direction")
