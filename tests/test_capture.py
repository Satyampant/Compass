import pytest
from sqlalchemy import func, select

from app.kernel import clock
from app.modules.capture import links, service
from app.modules.learning.models import LearningItem


def count_items(session):
    return session.scalar(select(func.count()).select_from(LearningItem))


def test_same_link_twice_leaves_one_item_pinned_to_top(session, fake_clock):
    first = service.capture(session, text="https://raft.github.io/", channel="web", key="a")
    fake_clock.advance(days=9)
    second = service.capture(
        session, text="Raft https://raft.github.io?utm_source=x", channel="telegram", key="b"
    )
    assert second.outcome == "duplicate"
    assert second.item.id == first.item.id
    assert count_items(session) == 1
    assert second.item.pinned_at == clock.now()


def test_same_key_is_stored_once(session, fake_clock):
    a = service.capture(session, text="https://a.com", channel="telegram", key="tg:1")
    b = service.capture(session, text="https://a.com", channel="telegram", key="tg:1")
    assert a.capture.id == b.capture.id and b.outcome == "item"
    assert count_items(session) == 1


def test_link_after_let_go_is_a_new_item(session, fake_clock):
    from app.modules.learning import lifecycle

    a = service.capture(session, text="https://a.com", channel="web", key="1")
    lifecycle.transition(session, a.item, "let_go")
    b = service.capture(session, text="https://a.com", channel="web", key="2")
    assert b.outcome == "item" and b.item.id != a.item.id


def test_link_with_text_uses_text_as_title(session, fake_clock):
    r = service.capture(
        session, text="Raft, visually explained https://youtu.be/abc?si=x", channel="tg", key="1"
    )
    assert r.item.title == "Raft, visually explained"
    assert r.item.source_type == "video"


@pytest.mark.parametrize("kind,outcome", [("learn", "item"), ("task", "task"), ("note", "note")])
def test_plain_text_waits_then_resolves(session, fake_clock, kind, outcome):
    r = service.capture(session, text="read about CRDTs", channel="telegram", key="1")
    assert r.outcome == "pending"
    r = service.resolve(session, r.capture, kind)
    assert r.outcome == outcome


def test_plain_text_with_kind_resolves_at_once(session, fake_clock):
    r = service.capture(session, text="Investor call", channel="web", key="1", kind="task")
    assert r.task.title == "Investor call"


@pytest.mark.parametrize(
    "a,b",
    [
        ("http://www.Example.com/post/", "https://example.com/post"),
        ("https://youtu.be/abc", "https://www.youtube.com/watch?v=abc&feature=share"),
        ("https://a.com/x?b=2&a=1#top", "https://a.com/x?a=1&b=2"),
    ],
)
def test_normalize(a, b):
    assert links.normalize(a) == links.normalize(b)
