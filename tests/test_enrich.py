import httpx
import pytest
from sqlalchemy import select

from app.kernel import scheduler
from app.kernel.models import Job
from app.modules.capture import enrich, service

PAGES = {
    "https://blog.example.com/raft": (
        200,
        "text/html",
        "<html><head><title>Raft &amp; consensus</title></head></html>",
    ),
    "https://og.example.com/a": (
        200,
        "text/html; charset=utf-8",
        '<meta property="og:title" content="OG title"><title>Plain</title>',
    ),
    "https://gone.example.com/x": (404, "text/html", "not found"),
}


def handle(request: httpx.Request) -> httpx.Response:
    if request.url.host == "www.youtube.com" and request.url.path == "/oembed":
        return httpx.Response(200, json={"title": "Raft, visually explained"})
    if request.url.host == "down.example.com":
        raise httpx.ConnectError("unreachable")
    status, ctype, body = PAGES[str(request.url)]
    return httpx.Response(status, headers={"content-type": ctype}, text=body)


@pytest.fixture(autouse=True)
def fake_web(monkeypatch):
    monkeypatch.setattr(
        enrich, "make_client", lambda: httpx.Client(transport=httpx.MockTransport(handle))
    )


def save(session, text):
    item = service.capture(session, text=text, channel="web", key=text).item
    session.commit()
    return item


def run_jobs(session, fake_clock, rounds=1):
    for _ in range(rounds):
        while scheduler.run_one(fake_clock.now()):
            pass
        fake_clock.advance(hours=1)
    session.expire_all()


def test_youtube_link_gets_title_and_video_type(session, fake_clock):
    item = save(session, "https://youtu.be/abc123")
    run_jobs(session, fake_clock)
    assert item.title == "Raft, visually explained"
    assert item.source_type == "video" and item.estimate_min == 20


@pytest.mark.parametrize(
    "url,title",
    [
        ("https://blog.example.com/raft", "Raft & consensus"),
        ("https://og.example.com/a", "OG title"),
    ],
)
def test_page_title(session, fake_clock, url, title):
    item = save(session, url)
    run_jobs(session, fake_clock)
    assert item.title == title


def test_missing_page_keeps_raw_link(session, fake_clock):
    item = save(session, "https://gone.example.com/x")
    run_jobs(session, fake_clock)
    assert item.title == "https://gone.example.com/x"


def test_unreachable_page_gives_up_after_five_tries(session, fake_clock):
    item = save(session, "https://down.example.com/x")
    run_jobs(session, fake_clock, rounds=8)
    assert item.title == "https://down.example.com/x"
    job = session.scalars(select(Job).where(Job.kind == "enrich_item")).one()
    assert job.status == "failed" and job.attempts == 5


def test_shared_text_title_is_kept(session, fake_clock):
    item = save(session, "My own name https://blog.example.com/raft")
    run_jobs(session, fake_clock)
    assert item.title == "My own name"
