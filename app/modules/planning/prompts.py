"""Planning prompts: next quarter from the 24th of a quarter's last month, next year from
1 December. A prompt stays open until the period starts, or until it has goals."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.planning.models import Goal
from app.modules.planning.periods import period

QUARTER_OPENS_ON_DAY = 24
YEAR_OPENS_ON = (12, 1)


def coming(today: date) -> list[tuple[str, date, date]]:
    """(horizon, start of the coming period, the day its prompt opens)."""
    _, q_end = period("quarter", today)
    _, y_end = period("year", today)
    return [
        ("quarter", q_end + timedelta(days=1), q_end.replace(day=QUARTER_OPENS_ON_DAY)),
        ("year", y_end + timedelta(days=1), date(today.year, *YEAR_OPENS_ON)),
    ]


def label(horizon: str, start: date) -> str:
    return str(start.year) if horizon == "year" else f"Q{(start.month - 1) // 3 + 1} {start.year}"


def has_goals(session: Session, horizon: str, start: date) -> bool:
    found = session.scalar(
        select(Goal.id).where(Goal.horizon == horizon, Goal.period_start == start).limit(1)
    )
    return found is not None


def open_prompts(session: Session, today: date) -> list[dict]:
    """The prompts open today, year first."""
    rows = [
        {"horizon": horizon, "starts": start, "label": label(horizon, start)}
        for horizon, start, opens in coming(today)
        if today >= opens and not has_goals(session, horizon, start)
    ]
    return sorted(rows, key=lambda r: r["horizon"] != "year")
