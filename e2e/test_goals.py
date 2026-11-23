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
