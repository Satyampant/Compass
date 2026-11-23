from datetime import date

import pytest

from app.modules.planning import service
from app.modules.planning.periods import period
from app.modules.planning.service import GoalError, KeyResultIn

DAY = date(2026, 11, 23)
KR = [KeyResultIn("Engine parity on 500 strategies", 500)]


def chain(session):
    year = service.create_goal(session, "year", "Make Tradl the OS", DAY)
    quarter = service.create_goal(
        session, "quarter", "Ship Backtest v1", DAY, parent_id=year.id, key_results=KR
    )
    month = service.create_goal(session, "month", "Parity green", DAY, parent_id=quarter.id)
    week = service.create_goal(session, "week", "Corporate actions", DAY, parent_id=month.id)
    return year, quarter, month, week


def test_periods():
    assert period("year", DAY) == (date(2026, 1, 1), date(2026, 12, 31))
    assert period("quarter", DAY) == (date(2026, 10, 1), date(2026, 12, 31))
    assert period("quarter", date(2026, 2, 3)) == (date(2026, 1, 1), date(2026, 3, 31))
    assert period("month", DAY) == (date(2026, 11, 1), date(2026, 11, 30))
    assert period("week", DAY) == (date(2026, 11, 23), date(2026, 11, 29))


def test_full_chain(session, fake_clock):
    year, quarter, month, week = chain(session)
    assert week.parent_id == month.id and month.parent_id == quarter.id
    assert quarter.period_start == date(2026, 10, 1)


def test_weekly_outcome_needs_a_parent(session, fake_clock):
    with pytest.raises(GoalError, match="needs a month parent"):
        service.create_goal(session, "week", "Ship it", DAY)


def test_parent_must_be_one_horizon_up(session, fake_clock):
    year, quarter, month, week = chain(session)
    with pytest.raises(GoalError, match="needs a month parent"):
        service.create_goal(session, "week", "x", DAY, parent_id=quarter.id)
    with pytest.raises(GoalError, match="no parent"):
        service.create_goal(session, "year", "x", DAY, parent_id=year.id)


def test_fourth_theme_is_refused(session, fake_clock):
    for i in range(3):
        service.create_goal(session, "year", f"Theme {i}", DAY)
    with pytest.raises(GoalError, match="at most 3 themes a year"):
        service.create_goal(session, "year", "Theme 4", DAY)
    service.create_goal(session, "year", "Next year", date(2027, 1, 5))


def test_quarter_and_week_limits(session, fake_clock):
    year, quarter, month, week = chain(session)
    for i in range(4):
        service.create_goal(session, "quarter", f"Q{i}", DAY, parent_id=year.id, key_results=KR)
    with pytest.raises(GoalError, match="at most 5 goals a quarter"):
        service.create_goal(session, "quarter", "Q6", DAY, parent_id=year.id, key_results=KR)
    for i in range(2):
        service.create_goal(session, "week", f"W{i}", DAY, parent_id=month.id)
    with pytest.raises(GoalError, match="at most 3 outcomes a week"):
        service.create_goal(session, "week", "W4", DAY, parent_id=month.id)
    for i in range(6):
        service.create_goal(session, "month", f"M{i}", DAY, parent_id=quarter.id)


def test_key_results_one_to_three(session, fake_clock):
    year = service.create_goal(session, "year", "Theme", DAY)
    with pytest.raises(GoalError, match="one to three"):
        service.create_goal(session, "quarter", "Q", DAY, parent_id=year.id)
    goal = service.create_goal(session, "quarter", "Q", DAY, parent_id=year.id, key_results=KR * 2)
    service.add_key_result(session, goal, KeyResultIn("Third", 1))
    with pytest.raises(GoalError, match="at most three"):
        service.add_key_result(session, goal, KeyResultIn("Fourth", 1))
    with pytest.raises(GoalError, match="only quarter"):
        service.add_key_result(session, year, KeyResultIn("x", 1))
