from datetime import timedelta

import pytest
from sqlalchemy import select

from app.kernel import clock
from app.kernel.models import Event
from app.modules.learning import lifecycle
from app.modules.learning.lifecycle import MOVES, TransitionError

STATES = ["inbox", "booked", "learning", "learned", "let_go", "expired"]
ACTIONS = ["book", "start", "finish", "unbook", "let_go", "expire"]


def make(session, state):
    item = lifecycle.create(session, title="Raft", captured_at=clock.now())
    item.state = state
    return item


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("action", ACTIONS)
def test_every_move(session, fake_clock, state, action):
    item = make(session, state)
    target = MOVES.get((state, action))
    kwargs = {"booked_for": clock.now() + timedelta(days=1)} if action == "book" else {}
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
