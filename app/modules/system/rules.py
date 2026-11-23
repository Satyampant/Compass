"""The rules from PRD section 08 as editable settings, each with a check.

Changing the learning slots or their length takes effect at once: upcoming slots that no
longer match are removed (their items keep their booking and move), and the calendar cycle
makes and fills the new ones.
"""

from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, settings
from app.modules.day import blocks
from app.modules.day.models import TimeBlock


class RuleError(ValueError):
    """A value that does not fit its rule."""


def hhmm(v) -> None:
    if not isinstance(v, str):
        raise RuleError("expected a time like 16:00")
    try:
        time.fromisoformat(v)
    except ValueError as exc:
        raise RuleError("expected a time like 16:00") from exc


def count(lo: int, hi: int):
    def check(v) -> None:
        if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
            raise RuleError(f"expected a whole number from {lo} to {hi}")

    return check


def days_list(v) -> None:
    if not isinstance(v, list) or not v or any(not isinstance(d, int) or d < 1 for d in v):
        raise RuleError("expected days after capture, like 3, 7, 14")
    if v != sorted(set(v)):
        raise RuleError("days must rise, like 3, 7, 14")


def slots(v) -> None:
    if not isinstance(v, list) or not v:
        raise RuleError("expected at least one learning slot")
    for s in v:
        if not isinstance(s, dict) or s.get("weekday") not in range(7):
            raise RuleError("each slot needs a weekday from 0 (Monday) to 6 (Sunday)")
        hhmm(s.get("time"))


def window(v) -> None:
    if not isinstance(v, list) or len(v) != 2:
        raise RuleError("expected a start and an end")
    hhmm(v[0])
    hhmm(v[1])
    if v[0] >= v[1]:
        raise RuleError("the day must end after it starts")


def zone(v) -> None:
    try:
        ZoneInfo(v)
    except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
        raise RuleError("expected a time zone like Asia/Kolkata") from exc


def folder(v) -> None:
    if v is not None and not isinstance(v, str):
        raise RuleError("expected a folder path")


RULES = {
    "resurface_days": days_list,
    "last_ask_day": count(1, 365),
    "last_ask_grace_days": count(0, 30),
    "revisit_per_day": count(1, 20),
    "default_estimate_min": count(1, 600),
    "max_in_learning": count(1, 10),
    "learning_slots": slots,
    "learning_block_min": count(15, 240),
    "day_window": window,
    "capacity_weekday_hours": count(0, 24),
    "capacity_weekend_hours": count(0, 24),
    "capacity_week_hours": count(0, 168),
    "top_priorities": count(1, 10),
    "morning_run_time": hhmm,
    "shutdown_nudge_time": hhmm,
    "block_reminder_min": count(0, 120),
    "nudges_per_day": count(0, 20),
    "pace_on_track_points": count(0, 100),
    "pace_at_risk_points": count(0, 100),
    "review_time": hhmm,
    "timezone": zone,
    "backup_dir": folder,
}
SLOT_KEYS = {"learning_slots", "learning_block_min"}


def current(session: Session) -> dict:
    return {key: settings.get(session, key) for key in RULES}


def update(session: Session, changes: dict) -> dict:
    """Check every change first, then store them all. Returns the new values."""
    unknown = set(changes) - set(RULES)
    if unknown:
        raise RuleError(f"unknown setting {sorted(unknown)[0]}")
    for key, value in changes.items():
        try:
            RULES[key](value)
        except RuleError as exc:
            raise RuleError(f"{key}: {exc}") from exc
    merged = {**current(session), **changes}
    if merged["pace_on_track_points"] > merged["pace_at_risk_points"]:
        raise RuleError("pace_on_track_points must not exceed pace_at_risk_points")
    slots_changed = any(changes[k] != settings.get(session, k) for k in SLOT_KEYS & set(changes))
    for key, value in changes.items():
        settings.put(session, key, value)
    if slots_changed:
        reslot(session)
    return current(session)


def reslot(session: Session) -> None:
    """Remove upcoming slots that no longer match the settings, freeing their items."""
    from app.modules.autopilot import cycle, protect

    tz = settings.tz(session)
    length = settings.get(session, "learning_block_min")
    upcoming = session.scalars(
        select(TimeBlock).where(
            TimeBlock.protected.is_(True),
            TimeBlock.start > clock.now(),
            TimeBlock.status.in_(("planned", "not_kept")),
        )
    )
    for slot in upcoming:
        monday = clock.week_start(slot.slot_at.astimezone(tz).date())
        wanted = protect.nominal_slots(session, monday)
        minutes = (slot.end - slot.start).total_seconds() / 60
        if slot.slot_at not in wanted or minutes != length:
            blocks.change(session, slot, item_id=None)
            blocks.remove(session, slot)
    session.flush()
    cycle.run(session)
