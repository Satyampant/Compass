"""HTTP API for the weekly review."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.kernel import settings
from app.kernel.db import SessionDep
from app.modules.learning.router import ItemOut, item_out
from app.modules.planning.router import GoalOut, goal_out
from app.modules.review import metrics, service
from app.modules.review.models import Review

router = APIRouter(prefix="/v1/reviews", tags=["review"])


class ReviewOut(BaseModel):
    week_start: date
    week_end: date
    week_number: int
    prepared_at: datetime | None
    closed_at: datetime | None
    numbers: dict
    answers: dict
    expired: list[ItemOut]
    oldest: list[ItemOut]
    drafts: list[GoalOut] = []


class AnswersIn(BaseModel):
    answers: dict[str, str]


def review_out(session: Session, review: Review, drafts=()) -> ReviewOut:
    monday = review.week_start
    return ReviewOut(
        week_start=monday,
        week_end=monday + timedelta(days=6),
        week_number=monday.isocalendar().week,
        prepared_at=review.prepared_at,
        closed_at=review.closed_at,
        numbers=service.numbers(session, review),
        answers=review.answers or {},
        expired=[item_out(session, i) for i in service.expired_in(session, monday)],
        oldest=[item_out(session, i) for i in service.oldest_inbox(session)],
        drafts=[goal_out(session, g) for g in drafts],
    )


def current_week(session: Session) -> date:
    """This week, except early in the week while last week is still open."""
    today = settings.today(session)
    monday = service.week_of(today)
    last = session.get(Review, monday - timedelta(days=7))
    if today.weekday() <= 1 and (last is None or last.closed_at is None):
        return monday - timedelta(days=7)
    return monday


def load(session: Session, week: date) -> Review:
    if week.weekday() != 0:
        raise HTTPException(422, "a week starts on a Monday")
    return service.get_or_create(session, week)


class DayMark(BaseModel):
    date: date
    planned: bool
    closed: bool


class WeekFlow(BaseModel):
    week_start: date
    added: int
    closed: int


class History(BaseModel):
    days: list[DayMark]
    weeks: list[WeekFlow]


@router.get("/history")
def history(session: SessionDep) -> History:
    """Twelve weeks of planned and closed days, and eight weeks of queue flow."""
    today = settings.today(session)
    monday = service.week_of(today)
    planned, closed = metrics.planned_days(session), metrics.closed_days(session)
    first = monday - timedelta(weeks=11)
    days = [first + timedelta(days=n) for n in range(84)]
    weeks = [monday - timedelta(weeks=n) for n in range(7, -1, -1)]
    flows = []
    for w in weeks:
        added, out = metrics.queue_flow(session, w, w + timedelta(days=6))
        flows.append(WeekFlow(week_start=w, added=added, closed=out))
    return History(
        days=[DayMark(date=d, planned=d in planned, closed=d in closed) for d in days],
        weeks=flows,
    )


@router.get("/current")
def current(session: SessionDep) -> ReviewOut:
    review = load(session, current_week(session))
    session.commit()
    return review_out(session, review)


@router.get("/{week}")
def get_review(week: date, session: SessionDep) -> ReviewOut:
    review = load(session, week)
    session.commit()
    return review_out(session, review)


@router.put("/{week}/answers")
def save_answers(week: date, body: AnswersIn, session: SessionDep) -> ReviewOut:
    review = load(session, week)
    try:
        service.save_answers(review, body.answers)
    except service.ReviewError as exc:
        raise HTTPException(409, str(exc)) from exc
    session.commit()
    return review_out(session, review)


@router.post("/{week}/close")
def close_week(week: date, session: SessionDep) -> ReviewOut:
    review = load(session, week)
    try:
        drafts = service.close(session, review)
    except service.ReviewError as exc:
        raise HTTPException(409, str(exc)) from exc
    session.commit()
    return review_out(session, review, drafts)
