from datetime import date, timedelta

import httpx
from playwright.sync_api import expect

from e2e.conftest import shot

TOMORROW = date.today() + timedelta(days=1)


def test_plan_tomorrow_needs_a_decision_for_each_open_task(page, server):
    for title in ("Split parity", "Investor call", "License review", "Cap table v3"):
        httpx.post(f"{server}/v1/tasks", json={"title": title})
    page.reload()
    page.locator("header.bar").get_by_role("button", name="Plan tomorrow").click()
    dialog = page.locator("dialog")
    finish = dialog.get_by_role("button", name="4 left to decide")
    expect(finish).to_be_disabled()

    dialog.get_by_role("radiogroup", name="Decision for Split parity").get_by_role(
        "radio", name="Tomorrow"
    ).click()
    dialog.get_by_role("radiogroup", name="Decision for Investor call").get_by_role(
        "radio", name="Tomorrow"
    ).click()
    dialog.get_by_role("radiogroup", name="Decision for License review").get_by_role(
        "radio", name="Pick a day"
    ).click()
    dialog.get_by_label("New day for License review").fill(
        (TOMORROW + timedelta(days=2)).isoformat()
    )
    expect(dialog.get_by_role("button", name="1 left to decide")).to_be_disabled()
    dialog.get_by_role("radiogroup", name="Decision for Cap table v3").get_by_role(
        "radio", name="Drop"
    ).click()
    shot(page, "plan-step1")
    dialog.get_by_role("button", name="Next: top three").click()

    dialog.get_by_role("button", name="Investor call").click()
    dialog.get_by_role("button", name="Split parity").click()
    shot(page, "plan-step2")
    dialog.get_by_role("button", name="Next: place blocks").click()
    expect(dialog.get_by_label("Start of Investor call")).to_have_value("08:00")
    dialog.get_by_label("Start of Split parity").fill("10:00")
    shot(page, "plan-step3")
    dialog.get_by_role("button", name="Commit plan").click()
    expect(page.locator(".toast")).to_contain_text("Tomorrow is planned")

    expect(page.locator(".task")).to_have_count(0)
    tasks = httpx.get(f"{server}/v1/days/{TOMORROW.isoformat()}/plan").json()["planned"]
    assert [(t["title"], t["top_rank"]) for t in tasks] == [
        ("Investor call", 1),
        ("Split parity", 2),
    ]
    blocks = httpx.get(f"{server}/v1/days/{TOMORROW.isoformat()}/plan").json()["blocks"]
    assert [(b["title"], b["start"][11:16]) for b in blocks] == [
        ("Investor call", "02:30"),
        ("Split parity", "04:30"),
    ]


def test_shutdown_closes_the_day(page):
    """Runs after planning above, so step three is already ticked."""
    card = page.locator(".ritual")
    expect(card.get_by_label("Pick tomorrow’s top three")).to_be_checked()
    fourth = card.get_by_label("Write one line: what did I learn?")
    expect(fourth).to_be_disabled()
    card.get_by_label("Mark what got done, move what didn’t").check()
    card.get_by_label("Decide on today’s captures").check()
    expect(fourth).to_be_disabled()
    card.get_by_label("What did I learn today").fill(
        "Corporate actions shift every price before the ex-date"
    )
    fourth.check()
    expect(card.locator(".chip")).to_contain_text("Closed")
    page.reload()
    expect(page.locator(".ritual .learned")).to_have_text(
        "Corporate actions shift every price before the ex-date"
    )
    shot(page, "shutdown")
