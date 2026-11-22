"""Fetch a saved page's title without AI. Runs as a job after each link capture."""

import html
import re
from urllib.parse import urlsplit

import httpx
from sqlalchemy.orm import Session

from app.kernel import jobs
from app.modules.learning.models import LearningItem

USER_AGENT = "Mozilla/5.0 (compatible; Compass/0.1)"
MAX_BYTES = 512_000
OG_TITLE = re.compile(
    r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"']([^\"']+)", re.IGNORECASE
)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def make_client() -> httpx.Client:
    """The HTTP client used for fetching. Tests replace it."""
    return httpx.Client(timeout=10, follow_redirects=True, headers={"User-Agent": USER_AGENT})


def fetch_title(client: httpx.Client, url: str) -> str | None:
    """The page title, or None if the page answers but has none. Network errors raise."""
    if (urlsplit(url).hostname or "").lower() in YOUTUBE_HOSTS:
        r = client.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"})
        return r.json().get("title") if r.status_code == 200 else None
    r = client.get(url)
    if r.status_code >= 400 or "html" not in r.headers.get("content-type", ""):
        return None
    page = r.text[:MAX_BYTES]
    match = OG_TITLE.search(page) or TITLE.search(page)
    return " ".join(html.unescape(match.group(1)).split()) if match else None


@jobs.handler("enrich_item")
def enrich_item(session: Session, payload: dict) -> None:
    """Give an item its page title if it still shows the raw link."""
    item = session.get(LearningItem, payload["item_id"])
    if item is None or not item.url or item.title != item.url:
        return
    with make_client() as client:
        title = fetch_title(client, item.url)
    if title:
        item.title = title[:300]
