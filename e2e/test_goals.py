import re
from datetime import date

from playwright.sync_api import expect

from e2e.conftest import shot
from e2e.test_web import settle


def go(page, name):
    page.goto(page.url.split("#")[0] + f"#{name}")
    page.wait_for_selector(".pagehead h1")


def test_year_quarter_month_flow(page):
    go(page, "year")
    page.get_by_role("button", name="Add a theme").click()
    page.get_by_label("Year theme title").fill("Make Tradl the OS for retail traders")
    page.get_by_label("Short label").fill("Company")
    page.get_by_role("button", name="Save").click()
    expect(page.locator(".theme h2", has_text="Make Tradl")).to_be_visible()

    go(page, "quarter")
    page.get_by_role("button", name="Add a goal").click()
    page.get_by_label("Quarter goal title").fill("Ship Equity Backtest v1.0")
    page.get_by_label("Parent goal").select_option(label="Make Tradl the OS for retail traders")
    page.get_by_label("Short label").fill("Backtest")
    page.get_by_label("Key result 1").fill("Engine parity on strategies")
    page.get_by_label("Target 1").fill("500")
    page.get_by_role("button", name="Save").click()
    goal = page.locator(".goal", has_text="Ship Equity Backtest")
    expect(goal.locator(".figure")).to_have_text("0%")

    goal.get_by_role("button", name="0 / 500").click()
    page.get_by_label("Current value for Engine parity on strategies").fill("310")
    page.keyboard.press("Enter")
    expect(goal.locator(".figure")).to_have_text("62%")
    settle(page)
    page.reload()
    expect(page.locator(".goal .figure")).to_have_text("62%")
    expect(page.locator(".goal aside .chip")).to_have_text(re.compile("On track|At risk|Behind"))
    expect(page.locator(".goal .pace em")).to_have_count(1)
    shot(page, "quarter")

    go(page, "month")
    page.get_by_role("button", name="Add").click()
    page.get_by_label("Milestone title").fill("Parity tests green")
    page.get_by_label("Due date").fill(date.today().isoformat())
    page.get_by_role("button", name="Save").click()
    expect(page.locator(".cal .d.today .ev", has_text="Parity tests green")).to_be_visible()
    page.get_by_role("button", name="Complete Parity tests green").click()
    expect(page.get_by_text("1 / 1 milestones")).to_be_visible()
    shot(page, "month")

    go(page, "year")
    expect(page.locator(".theme li", has_text="Ship Equity Backtest")).to_contain_text("62%")
    shot(page, "year")


def test_link_task_and_capture_to_goal(page):
    """Runs after the flow above, so the goal tree exists."""
    page.get_by_label("New task").fill("Split parity run")
    page.get_by_role("button", name="Add", exact=True).click()
    row = page.locator(".task", has_text="Split parity run")
    expect(row.locator(".untied")).to_have_text("Untied")
    row.locator(".taskbody").click()
    page.locator("#tgoal").select_option(label="Ship Equity Backtest v1.0")
    page.keyboard.press("Escape")
    expect(row.locator(".gtag")).to_have_text("Backtest")

    page.keyboard.press("c")
    page.locator("#ctitle").fill("https://clickhouse.example.com/mv")
    page.locator("#cgoal").select_option(label="Parity tests green")
    page.locator("#creason").fill("Faster candle roll-ups")
    page.get_by_role("button", name="Save to queue").click()
    expect(page.locator(".toast")).to_contain_text("Saved")
    go(page, "learn")
    expect(page.locator(".kcard", has_text="clickhouse").locator(".gtag")).to_have_text("Backtest")
    shot(page, "queue-tagged")


def test_top_three_focus_and_trace(page):
    """Runs after the tests above: "Split parity run" serves the quarter goal."""
    for title in ("Investor call", "License review", "Gym"):
        page.get_by_label("New task").fill(title)
        page.get_by_role("button", name="Add", exact=True).click()
        expect(page.locator(".task", has_text=title)).to_be_visible()
    expect(page.locator(".focus h2")).to_have_text("Choose today’s top three")
    for title in ("Split parity run", "Investor call", "License review"):
        page.get_by_role("button", name=f"Add to top three: {title}").click()
        settle(page)
    expect(page.locator(".focus h2")).to_have_text("Split parity run")
    expect(page.locator(".focus .trace a")).to_have_count(2)

    page.get_by_role("button", name="Add to top three: Gym").click()
    page.get_by_role("button", name="2. Investor call").click()
    settle(page)
    top = page.locator(".kicker.sub-k", has_text="Top three")
    expect(top).to_be_visible()
    expect(page.get_by_role("button", name="Remove from top three: Gym")).to_be_visible()
    expect(page.get_by_role("button", name="Add to top three: Investor call")).to_be_visible()
    shot(page, "today-focus")

    page.locator(".focus .trace a", has_text="Make Tradl").click()
    expect(page.locator(".pagehead h1")).to_have_text("This year")

    go(page, "today")
    page.locator(".task", has_text="Gym").locator(".taskbody").click()
    expect(page.locator("dialog .untied")).to_be_visible()
