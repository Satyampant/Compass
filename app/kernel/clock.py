"""The one source of the current time. Tests swap in a FakeClock."""

from datetime import UTC, date, datetime, timedelta


class Clock:
    """Real wall-clock time in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock(Clock):
    """A clock that only moves when told to."""

    def __init__(self, at: datetime):
        self.at = at

    def now(self) -> datetime:
        return self.at

    def set(self, at: datetime) -> None:
        self.at = at

    def advance(self, **kwargs) -> None:
        self.at += timedelta(**kwargs)


_clock: Clock = Clock()


def now() -> datetime:
    """Current time, aware, in UTC."""
    return _clock.now()


def use(clock: Clock) -> None:
    """Replace the clock, for tests."""
    global _clock
    _clock = clock


def local_date(at: datetime, tz) -> date:
    """The calendar date of a moment in the given time zone."""
    return at.astimezone(tz).date()


def week_start(day: date) -> date:
    """The Monday of the week containing day."""
    return day - timedelta(days=day.weekday())


def combine(day: date, tz) -> datetime:
    """Midnight at the start of a local date, as an aware moment."""
    return datetime.combine(day, datetime.min.time(), tz)
