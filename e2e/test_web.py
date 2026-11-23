import time

from playwright.sync_api import expect

from e2e.conftest import shot


def capture(page, text):
    page.keyboard.press("c")
    page.locator("#ctitle").fill(text)
    page.keyboard.press("Enter")


def card(page, column, title):
    return page.locator(f"section.col[aria-label='{column}'] .kcard", has_text=title)


def settle(page):
    """Wait until the move's API calls, and the refetches they trigger, have finished."""
    page.wait_for_timeout(50)
    page.wait_for_function("window.__inflight === 0")


def drag(page, source, column):
    box = source.bounding_box()
    target = page.locator(f"section.col[aria-label='{column}']").bounding_box()
    page.mouse.move(box["x"] + 20, box["y"] + 10)
    page.mouse.down()
    page.mouse.move(box["x"] + 40, box["y"] + 20, steps=4)
    page.mouse.move(target["x"] + target["width"] / 2, target["y"] + 60, steps=12)
    page.mouse.up()
    settle(page)


def test_first_day_prompt(page):
    expect(page.get_by_text("Share your first link to the Compass bot")).to_be_visible()
    shot(page, "today-empty")


def test_c_paste_enter_saves_in_under_five_seconds(page):
    start = time.monotonic()
    capture(page, "https://raft.github.io/")
    expect(page.locator(".toast")).to_contain_text("Saved")
    assert time.monotonic() - start < 5
    page.goto(page.url.split("#")[0] + "#learn")
    expect(card(page, "Inbox", "raft.github.io")).to_be_visible()


def test_capture_from_queue_screen_and_duplicate(page):
    page.goto(page.url + "#learn")
    capture(page, "https://raft.github.io")
    expect(page.locator(".toast")).to_contain_text("Already saved")
    expect(card(page, "Inbox", "raft.github.io")).to_have_count(1)


def test_every_move_by_clicks_and_by_drag(page):
    capture(page, "https://clicks.example.com/a")
    expect(page.locator(".toast")).to_contain_text("Saved")
    capture(page, "https://drag.example.com/b")
    expect(page.locator(".toast")).to_contain_text("Saved")
    page.goto(page.url.split("#")[0] + "#learn")

    # two clicks each: open, then the move
    card(page, "Inbox", "clicks.example.com").click()
    page.get_by_role("button", name="Book next learning block").click()
    expect(card(page, "Booked", "clicks.example.com")).to_be_visible()
    card(page, "Booked", "clicks.example.com").click()
    page.get_by_role("button", name="Back to inbox").click()
    expect(card(page, "Inbox", "clicks.example.com")).to_be_visible()
    card(page, "Inbox", "clicks.example.com").click()
    page.get_by_role("button", name="Book next learning block").click()
    card(page, "Booked", "clicks.example.com").click()
    page.get_by_role("button", name="Start now").click()
    expect(card(page, "Learning", "clicks.example.com")).to_be_visible()
    card(page, "Learning", "clicks.example.com").click()
    page.locator("#bnote").fill("Leader election finally makes sense")
    page.get_by_role("button", name="Mark learned").click()
    expect(card(page, "Learned", "Leader election finally makes sense")).to_be_visible()

    # drag
    drag(page, card(page, "Inbox", "drag.example.com"), "Booked")
    expect(card(page, "Booked", "drag.example.com")).to_be_visible()
    drag(page, card(page, "Booked", "drag.example.com"), "Inbox")
    expect(card(page, "Inbox", "drag.example.com")).to_be_visible()
    drag(page, card(page, "Inbox", "drag.example.com"), "Learning")
    expect(page.locator(".toast")).to_contain_text("Book it first")
    drag(page, card(page, "Inbox", "drag.example.com"), "Booked")
    expect(card(page, "Booked", "drag.example.com")).to_be_visible()
    drag(page, card(page, "Booked", "drag.example.com"), "Learning")
    expect(card(page, "Learning", "drag.example.com")).to_be_visible()
    drag(page, card(page, "Learning", "drag.example.com"), "Booked")
    expect(card(page, "Booked", "drag.example.com")).to_be_visible()
    drag(page, card(page, "Booked", "drag.example.com"), "Learning")
    expect(card(page, "Learning", "drag.example.com")).to_be_visible()
    drag(page, card(page, "Learning", "drag.example.com"), "Learned")
    expect(page.get_by_role("button", name="Mark learned")).to_be_disabled()
    page.locator("#bnote").fill("Notes saved")
    page.get_by_role("button", name="Mark learned").click()
    expect(card(page, "Learned", "Notes saved")).to_be_visible()
    shot(page, "queue")

    # let go
    capture(page, "https://letgo.example.com")
    expect(card(page, "Inbox", "letgo.example.com")).to_be_visible()
    card(page, "Inbox", "letgo.example.com").click()
    page.get_by_role("button", name="Let go").click()
    expect(card(page, "Inbox", "letgo.example.com")).to_have_count(0)


def test_task_added_by_quick_capture_appears_and_ticks(page):
    page.keyboard.press("c")
    page.get_by_role("radio", name="Task").click()
    page.locator("#ctitle").fill("Investor call")
    page.keyboard.press("Enter")
    row = page.locator(".task", has_text="Investor call")
    expect(row).to_be_visible()
    row.locator(".check").click()
    expect(row).to_have_class("task done")
    page.reload()
    expect(page.locator(".task.done", has_text="Investor call")).to_be_visible()
    shot(page, "today")


def test_dark_mode(browser, server):
    context = browser.new_context(color_scheme="dark", viewport={"width": 1360, "height": 900})
    pg = context.new_page()
    pg.goto(server + "/#learn")
    bg = pg.evaluate("getComputedStyle(document.body).backgroundColor")
    assert bg == "rgb(19, 25, 21)"
    shot(pg, "queue-dark")
    context.close()


def test_third_item_in_learning_asks_to_finish_or_return_one(page):
    page.goto(page.url.split("#")[0] + "#learn")
    for name in ("one", "two", "three"):
        capture(page, f"https://wip.example.com/{name}")
        expect(page.locator(".toast")).to_contain_text("Saved")
        drag(page, card(page, "Inbox", f"wip.example.com/{name}"), "Booked")
    for name in ("one", "two"):
        drag(page, card(page, "Booked", f"wip.example.com/{name}"), "Learning")
    drag(page, card(page, "Booked", "wip.example.com/three"), "Learning")
    dialog = page.locator("dialog")
    expect(dialog.get_by_role("heading")).to_have_text("Two items are in Learning")
    dialog.locator(".decide", has_text="wip.example.com/one").get_by_role(
        "button", name="Return to booked"
    ).click()
    settle(page)
    expect(card(page, "Learning", "wip.example.com/three")).to_be_visible()
    expect(card(page, "Booked", "wip.example.com/one")).to_be_visible()
