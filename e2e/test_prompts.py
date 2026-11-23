import httpx
from playwright.sync_api import expect

PROMPTS = '[{"horizon": "year", "starts": "2027-01-01", "label": "2027"}]'


def test_planning_prompt_banner_creates_next_years_theme(page, server):
    page.route(
        "**/v1/planning/prompts",
        lambda route: route.fulfill(status=200, content_type="application/json", body=PROMPTS),
    )
    page.reload()
    banner = page.get_by_test_id("planning-prompt")
    expect(banner).to_contain_text("2027 planning is open")
    banner.get_by_role("button", name="Plan 2027").click()
    page.get_by_label("Year theme title").fill("Make Tradl profitable")
    page.get_by_role("button", name="Save").click()
    expect(page.locator("dialog[open]")).to_have_count(0)
    themes = httpx.get(f"{server}/v1/goals?horizon=year&on=2027-03-01").json()
    assert [(t["title"], t["period_start"]) for t in themes] == [
        ("Make Tradl profitable", "2027-01-01")
    ]
