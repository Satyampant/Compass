from playwright.sync_api import expect

from e2e.conftest import shot


def test_status_page_shows_every_row(page):
    page.goto(page.url.split("#")[0] + "#status")
    for name in ("Morning run", "Telegram check", "Backup", "Calendar sync"):
        expect(page.get_by_test_id(f"status-{name}")).to_be_visible()
    expect(page.get_by_test_id("status-Backup")).to_contain_text("Check")
    shot(page, "status")


def test_download_all_data(page):
    page.goto(page.url.split("#")[0] + "#status")
    with page.expect_download() as info:
        page.get_by_role("link", name="Download all data").click()
    assert info.value.suggested_filename.startswith("compass-export-")
