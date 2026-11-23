"""The calendar period each horizon covers."""

from datetime import date, timedelta

from app.kernel.clock import week_start


def period(horizon: str, day: date) -> tuple[date, date]:
    """First and last date of the year, quarter, month or week containing day."""
    if horizon == "year":
        return date(day.year, 1, 1), date(day.year, 12, 31)
    if horizon == "quarter":
        first = 3 * ((day.month - 1) // 3) + 1
        return date(day.year, first, 1), _month_end(day.year, first + 2)
    if horizon == "month":
        return date(day.year, day.month, 1), _month_end(day.year, day.month)
    start = week_start(day)
    return start, start + timedelta(days=6)


def _month_end(year: int, month: int) -> date:
    nxt = date(year + month // 12, month % 12 + 1, 1)
    return nxt - timedelta(days=1)
