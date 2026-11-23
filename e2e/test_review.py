import httpx
from playwright.sync_api import expect

from e2e.conftest import shot
from e2e.test_web import settle


def test_close_the_week_and_see_next_weeks_drafts(page, server):
    httpx.post(f"{server}/v1/captures", json={"text": "https://raft.github.io"})
    page.goto(page.url.split("#")[0] + "#review")
    expect(page.locator(".pagehead h1")).to_contain_text("in review")
    expect(page.locator(".hbox", has_text="Queue in and out")).to_be_visible()
    expect(page.get_by_test_id("heat").locator("i")).to_have_count(84)
    page.get_by_label("What moved a goal forward?").fill("Fee model merged")
    page.get_by_label("What pulled me off course?").fill("Three unplanned calls")
    page.get_by_label("Next week’s top three").fill("Corporate actions parity\nMetrics pack")
    page.get_by_label("Next week’s top three").blur()
    settle(page)
    shot(page, "review")
    page.get_by_role("button", name="Close week").click()
    expect(page.locator(".toast")).to_contain_text("2 outcomes drafted")
    expect(page.get_by_label("What moved a goal forward?")).to_have_attribute("readonly", "")
    expect(page.locator(".chip", has_text="Closed")).to_be_visible()
    closed = page.locator(".pagehead h1").inner_text()
    page.reload()  # the next open week is now current
    expect(page.locator(".pagehead h1")).not_to_have_text(closed)
    expect(page.locator(".chip", has_text="Closed")).to_have_count(0)


def test_queue_flow_on_the_queue_page(page):
    page.goto(page.url.split("#")[0] + "#learn")
    expect(page.get_by_test_id("flow").locator(".flowweek")).to_have_count(8)
