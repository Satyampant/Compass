from datetime import timedelta

import pytest
from sqlalchemy import select

from app.kernel import clock
from app.kernel.models import Event
from app.modules.learning import lifecycle
from app.modules.learning.lifecycle import MOVES, TransitionError

STATES = ["inbox", "booked", "learning", "learned", "let_go", "expired"]
ACTIONS = ["book", "start", "finish", "return", "unbook", "let_go", "expire"]


def make(session, state):
    item = lifecycle.create(session, title="Raft", captured_at=clock.now())
    item.state = state
    return item


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("action", ACTIONS)
def test_every_move(session, fake_clock, state, action):
    item = make(session, state)
    target = MOVES.get((state, action))
    kwargs = {
        "booked_for": clock.now() + timedelta(days=1),
        "note": "Notes saved",
    }
    if target is None:
        with pytest.raises(TransitionError):
            lifecycle.transition(session, item, action, **kwargs)
        assert item.state == state
    else:
        lifecycle.transition(session, item, action, **kwargs)
        assert item.state == target
        event = session.scalars(select(Event).where(Event.kind == f"item.{action}")).one()
        assert event.data == {"from": state, "to": target}


def test_new_item_resurfaces_on_day_three(session, fake_clock):
    item = lifecycle.create(session, title="Raft", captured_at=clock.now())
    assert item.state == "inbox"
    assert item.next_resurface_at == clock.now() + timedelta(days=3)
    assert item.estimate_min == 20


def test_book_needs_a_time(session, fake_clock):
    with pytest.raises(TransitionError):
        lifecycle.transition(session, make(session, "inbox"), "book")


def test_unbook_puts_item_top_of_revisit(session, fake_clock):
    item = make(session, "inbox")
    lifecycle.transition(session, item, "book", booked_for=clock.now())
    lifecycle.transition(session, item, "unbook")
    assert item.pinned_at == clock.now() and item.booked_for is None


def test_person_cannot_expire(session):
    assert "expire" not in lifecycle.allowed_actions("inbox")
    assert lifecycle.allowed_actions("booked") == ["start", "unbook", "let_go"]


def learning(session, n):
    items = []
    for _ in range(n):
        item = make(session, "booked")
        lifecycle.transition(session, item, "start")
        items.append(item)
    return items


def test_cannot_reach_learned_without_a_note(session, fake_clock):
    (item,) = learning(session, 1)
    for note in (None, "", "   "):
        with pytest.raises(TransitionError, match="needs one line"):
            lifecycle.transition(session, item, "finish", note=note)
    assert item.state == "learning"
    lifecycle.transition(session, item, "finish", note=" Applied to alerts ")
    assert item.state == "learned" and item.note == "Applied to alerts"


def test_third_item_in_learning_is_refused(session, fake_clock):
    first, second = learning(session, 2)
    third = make(session, "booked")
    with pytest.raises(TransitionError, match="2 items are in Learning already"):
        lifecycle.transition(session, third, "start")
    lifecycle.transition(session, first, "return", booked_for=clock.now() + timedelta(days=2))
    assert first.state == "booked" and first.started_at is not None
    lifecycle.transition(session, third, "start")
    assert third.state == "learning"


def test_return_via_api_takes_next_slot(client, session, fake_clock):
    (item,) = learning(session, 1)
    session.commit()
    r = client.post(f"/v1/learning-items/{item.id}/transitions", json={"action": "return"})
    assert r.json()["state"] == "booked" and r.json()["booked_for"].startswith("2026-11-23T10:30")
    r = client.post(f"/v1/learning-items/{item.id}/transitions", json={"action": "start"})
    r = client.post(f"/v1/learning-items/{item.id}/transitions", json={"action": "finish"})
    assert r.status_code == 409 and "needs one line" in r.json()["detail"]
