from playwright.sync_api import expect

from e2e.conftest import shot


def add(page, label, title, **fields):
    page.get_by_label(f"{label} title").fill(title)
    for name, value in fields.items():
        field = page.get_by_label(name)
        if name == "Parent goal":
            field.select_option(label=value)
        else:
            field.fill(value)
    page.get_by_role("button", name="Add", exact=True).click()
    expect(page.locator(".setup-list li", has_text=title)).to_be_visible()


def test_guided_setup_from_nothing(page):
    page.get_by_role("link", name="Start setup").click()
    expect(page.get_by_role("button", name="Next")).to_be_disabled()
    add(page, "Year theme", "Make Tradl the OS for retail traders")
    add(page, "Year theme", "Build the life outside work")
    page.get_by_role("button", name="Next").click()

    add(
        page,
        "Quarter goal",
        "Ship Equity Backtest v1.0",
        **{
            "Parent goal": "Make Tradl the OS for retail traders",
            "Key result 1": "Parity",
            "Target 1": "500",
        },
    )
    page.get_by_role("button", name="Next").click()

    add(page, "Milestone", "Parity tests green", **{"Parent goal": "Ship Equity Backtest v1.0"})
    page.get_by_role("button", name="Next").click()

    add(page, "Weekly outcome", "Corporate actions parity", **{"Parent goal": "Parity tests green"})
    shot(page, "setup")
    page.get_by_role("button", name="Finish setup").click()
    expect(page.get_by_role("link", name="Start setup")).to_have_count(0)
    page.goto(page.url.split("#")[0] + "#year")
    expect(page.locator(".theme h2")).to_have_count(3)
