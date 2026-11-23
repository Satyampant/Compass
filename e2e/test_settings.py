import httpx
from playwright.sync_api import expect

from e2e.conftest import shot


def test_change_slots_and_rules_from_the_settings_screen(page, server):
    page.goto(page.url.split("#")[0] + "#settings")
    page.get_by_label("Slot 1 day").select_option(label="Tuesday")
    page.get_by_label("Slot 1 time").fill("07:30")
    page.get_by_label("top_priorities").fill("4")
    page.get_by_role("button", name="Save settings").click()
    expect(page.locator(".toast")).to_contain_text("Settings saved")
    values = httpx.get(f"{server}/v1/settings").json()
    assert values["learning_slots"][0] == {"weekday": 1, "time": "07:30"}
    assert values["top_priorities"] == 4
    page.reload()
    expect(page.get_by_label("Slot 1 time")).to_have_value("07:30")
    shot(page, "settings")

    page.get_by_label("resurface_days").fill("7, 3")
    page.get_by_role("button", name="Save settings").click()
    expect(page.locator(".toast")).to_contain_text("days must rise")
