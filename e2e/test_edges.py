"""PRD section 09 situations and keyboard paths, in the browser."""

import httpx
from playwright.sync_api import expect

from e2e.conftest import shot
from e2e.test_web import settle


def test_first_day_shows_one_prompt_and_no_goal_fields(page):
    expect(page.get_by_text("Share your first link to the Compass bot")).to_be_visible()
    expect(page.locator(".focus")).to_have_count(0)
    expect(page.get_by_text("Set your direction")).to_have_count(0)
    expect(page.get_by_text("Direction check")).to_have_count(0)
    page.keyboard.press("c")
    expect(page.locator("#cgoal")).to_have_count(0)
    page.keyboard.press("Escape")
    shot(page, "first-day")


def test_rename_an_item_whose_title_could_not_be_fetched(page, server):
    httpx.post(f"{server}/v1/captures", json={"text": "https://untitled.example.com/x"})
    page.goto(page.url.split("#")[0] + "#learn")
    page.locator(".kcard", has_text="untitled.example.com").click()
    page.get_by_role("button", name="Rename").click()
    page.get_by_label("Item title").fill("Order book internals")
    page.keyboard.press("Enter")
    settle(page)
    page.keyboard.press("Escape")
    expect(page.locator(".kcard", has_text="Order book internals")).to_be_visible()


def test_move_a_task_to_another_day_with_the_keyboard(page, server):
    page.get_by_label("New task").fill("Cap table v3")
    page.keyboard.press("Enter")
    row = page.locator(".task", has_text="Cap table v3")
    row.locator(".taskbody").focus()
    page.keyboard.press("Enter")
    page.locator("#tday").fill("2030-01-07")
    settle(page)
    page.keyboard.press("Escape")
    expect(row).to_have_count(0)
    tasks = httpx.get(f"{server}/v1/week?on=2030-01-07").json()["days"][0]["tasks"]
    assert [t["title"] for t in tasks] == ["Cap table v3"]


def test_deleting_a_goal_asks_its_children_for_a_new_parent(page, server):
    year = httpx.post(f"{server}/v1/goals", json={"horizon": "year", "title": "Theme"}).json()
    q = httpx.post(
        f"{server}/v1/goals",
        json={
            "horizon": "quarter",
            "title": "Old goal",
            "parent_id": year["id"],
            "key_results": [{"title": "k", "target": 1}],
        },
    ).json()
    httpx.post(
        f"{server}/v1/goals",
        json={
            "horizon": "quarter",
            "title": "New goal",
            "parent_id": year["id"],
            "key_results": [{"title": "k", "target": 1}],
        },
    )
    httpx.post(
        f"{server}/v1/goals",
        json={"horizon": "month", "title": "Milestone A", "parent_id": q["id"]},
    )
    page.goto(page.url.split("#")[0] + "#quarter")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Delete Old goal").click()
    settle(page)
    page.goto(page.url.split("#")[0] + "#month")
    expect(page.get_by_text("Needs a quarter goal")).to_be_visible()
    page.get_by_label("Parent for Milestone A").select_option(label="New goal")
    expect(page.get_by_text("Needs a quarter goal")).to_have_count(0)
    expect(page.locator(".task", has_text="Milestone A")).to_be_visible()
