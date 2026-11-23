import os
import subprocess
import time

import httpx
import pytest
from playwright.sync_api import sync_playwright

PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
SHOTS = os.environ.get("COMPASS_SHOTS")
INFLIGHT = """
window.__inflight = 0;
const f = window.fetch;
window.fetch = (...a) => {
  window.__inflight++;
  return f(...a).finally(() => window.__inflight--);
};
"""


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """The real app on a throwaway database per test module, without the scheduler or the bot."""
    db = tmp_path_factory.mktemp("e2e") / "e2e.db"
    env = {**os.environ, "COMPASS_DB_URL": f"sqlite:///{db}", "COMPASS_BACKGROUND": "0"}
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        try:
            if httpx.get(f"{BASE}/healthz").status_code == 200:
                break
        except httpx.TransportError:
            time.sleep(0.2)
    yield BASE
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser, server):
    context = browser.new_context(viewport={"width": 1360, "height": 900})
    context.add_init_script(INFLIGHT)
    pg = context.new_page()
    pg.goto(server)
    pg.wait_for_selector(".pagehead")
    yield pg
    context.close()


def shot(page, name):
    """Save a screenshot when COMPASS_SHOTS names a folder."""
    if SHOTS:
        page.screenshot(path=f"{SHOTS}/{name}.png", full_page=True)
