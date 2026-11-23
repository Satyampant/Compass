"""The weekly review: the week's numbers, the four answers, and closing the week.

An open week's numbers are computed live. Closing the week freezes them in a snapshot, so a
task finished later does not change a closed week. The fourth answer, next week's top three,
becomes next week's draft outcomes.
"""

import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel import clock, events, jobs, settings
from app.modules.day.models import Task, TimeBlock
from app.modules.learning.models import LearningItem
from app.modules.notify.service import Nudge, send_nudges
from app.modules.planning import service as planning
from app.modules.planning.models import Goal
from app.modules.planning.tags import tag_for
from app.modules.review import metrics
from app.modules.review.models import Review

PROMPTS = ("moved", "off_course", "still_matter", "next_top")
OLDEST = 5


class ReviewError(ValueError):
    """A change to a week that is already closed."""


def week_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def hours_by_goal(session: Session, monday: date) -> list[dict]:
    """Planned and done minutes per quarter goal, untied last."""
    sunday = monday + timedelta(days=6)
    groups: dict[int | None, dict] = {}

    def add(goal_id, minutes, done):
        tag = tag_for(session, goal_id)
        key = tag.id if tag else None
        row = groups.setdefault(
            key, {"tag": tag.model_dump() if tag else None, "planned_min": 0, "done_min": 0}
        )
        row["planned_min"] += minutes
        row["done_min"] += minutes if done else 0

    for t in session.scalars(
        select(Task).where(Task.planned_date.between(monday, sunday), Task.dropped_at.is_(None))
    ):
        add(t.goal_id, t.estimate_min, t.done_at is not None)
    tz = settings.tz(session)
    first = clock.combine(monday, tz)
    for b in session.scalars(
        select(TimeBlock).where(
            TimeBlock.kind == "learning",
            TimeBlock.item_id.is_not(None),
            TimeBlock.start >= first,
            TimeBlock.start < first + timedelta(days=7),
        )
    ):
        item = session.get(LearningItem, b.item_id)
        minutes = int((b.end - b.start).total_seconds() // 60)
        add(item.goal_id, minutes, b.status in ("started", "kept"))
    return sorted(groups.values(), key=lambda r: (r["tag"] is None, -r["planned_min"]))


def week_numbers(session: Session, monday: date) -> dict:
    """The review's numbers for a week, computed now."""
    days = [monday + timedelta(days=n) for n in range(7)]
    per_day = [metrics.day_numbers(session, d) for d in days]
    kept, total = metrics.blocks_kept(metrics.week_slots(session, monday))
    captured, closed = metrics.queue_flow(session, days[0], days[-1])
    return {
        "top_done": sum(n.top_done for n in per_day),
        "top_planned": sum(n.top_planned for n in per_day),
        "aligned_min": sum(n.aligned_min for n in per_day),
        "planned_min": sum(n.planned_min for n in per_day),
        "blocks_kept": kept,
        "blocks_total": total,
        "captured": captured,
        "closed": closed,
        "hours_by_goal": hours_by_goal(session, monday),
    }


def get_or_create(session: Session, monday: date) -> Review:
    review = session.get(Review, monday)
    if review is None:
        review = Review(week_start=monday, answers={})
        session.add(review)
        session.flush()
    return review


def numbers(session: Session, review: Review) -> dict:
    """Frozen numbers for a closed week, live ones otherwise."""
    return review.snapshot if review.closed_at else week_numbers(session, review.week_start)


def expired_in(session: Session, monday: date) -> list[LearningItem]:
    tz = settings.tz(session)
    first = clock.combine(monday, tz)
    return list(
        session.scalars(
            select(LearningItem)
            .where(
                LearningItem.state == "expired",
                LearningItem.closed_at >= first,
                LearningItem.closed_at < first + timedelta(days=7),
            )
            .order_by(LearningItem.closed_at)
        )
    )


def oldest_inbox(session: Session) -> list[LearningItem]:
    return list(
        session.scalars(
            select(LearningItem)
            .where(LearningItem.state == "inbox")
            .order_by(LearningItem.captured_at)
            .limit(OLDEST)
        )
    )


def save_answers(review: Review, answers: dict[str, str]) -> None:
    if review.closed_at:
        raise ReviewError("this week is closed")
    review.answers = {k: (answers.get(k) or "").strip() for k in PROMPTS}


def outcome_lines(text: str) -> list[str]:
    """Up to three outcomes from free text: one per line, or '1. a 2. b 3. c' on one line."""
    parts = re.split(r"\n|(?:^|\s)\d+[.)]\s+", text)
    lines = [p.strip(" -•\t") for p in parts]
    return [line for line in lines if line][:3]


def close(session: Session, review: Review) -> list[Goal]:
    """Freeze the numbers and draft next week's outcomes from the fourth answer."""
    if review.closed_at:
        raise ReviewError("this week is already closed")
    review.snapshot = week_numbers(session, review.week_start)
    review.closed_at = clock.now()
    next_monday = review.week_start + timedelta(days=7)
    room = planning.LIMITS["week"] - len(
        session.scalars(
            select(Goal.id).where(Goal.horizon == "week", Goal.period_start == next_monday)
        ).all()
    )
    drafts = [
        planning.create_goal(session, "week", line, next_monday, draft=True)
        for line in outcome_lines(review.answers.get("next_top", ""))[: max(room, 0)]
    ]
    events.record(session, "review.closed", "review", None, week=review.week_start.isoformat())
    return drafts


@jobs.handler("review_prepare")
def review_prepare(session: Session, payload: dict) -> None:
    """Job: on Sunday at 18:00, or the next wake, have the week's review waiting."""
    day = date.fromisoformat(payload["day"])
    if day.weekday() != 6:
        return
    review = get_or_create(session, week_of(day))
    if review.prepared_at is None:
        review.prepared_at = clock.now()
        send_nudges(session, [Nudge("review", "Your weekly review is ready. About 20 minutes.")])
