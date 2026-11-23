import json
from pathlib import Path

import httpx

EXTENSION = Path(__file__).resolve().parents[1] / "extension"


def test_one_click_saves_the_tab_with_duplicate_handling(server, pw, tmp_path):
    context = pw.chromium.launch_persistent_context(
        tmp_path / "profile",
        headless=True,
        channel="chromium",
        args=[f"--disable-extensions-except={EXTENSION}", f"--load-extension={EXTENSION}"],
    )
    worker = context.service_workers[0] if context.service_workers else None
    worker = worker or context.wait_for_event("serviceworker")
    tab = {"url": "https://raft.github.io/", "title": "Raft consensus, visually explained"}
    save = f"(tab) => self.saveTab(tab, {json.dumps(server)})"
    first = worker.evaluate(save, tab)
    second = worker.evaluate(save, tab)
    blocked = worker.evaluate(save, {"url": "chrome://settings", "title": "Settings"})
    context.close()
    assert first["outcome"] == "item" and first["title"] == "Raft consensus, visually explained"
    assert second["outcome"] == "duplicate" and second["item_id"] == first["item_id"]
    assert blocked["outcome"] == "error"
    inbox = httpx.get(f"{server}/v1/learning-items?state=inbox").json()
    assert [i["title"] for i in inbox].count("Raft consensus, visually explained") == 1
