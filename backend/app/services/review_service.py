"""Applies every graded answer to the learning record: item status, best score, and the
subtopic's next review date (SM-2)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.orm_models import LearningItemRow, ReviewScheduleRow
from app.learning.item_status import LearningStatus, status_after_score
from app.learning.spaced_repetition import ReviewState, schedule_after_review


def record_outcome(session: Session, item: LearningItemRow, score: float, today: date | None = None) -> None:
    """Call after saving an attempt. Commits."""
    today = today or date.today()
    item.status = status_after_score(score, LearningStatus(item.status)).value
    item.best_score = max(score, item.best_score or 0.0)

    row = _get_schedule(session, item.track_id, item.subtopic_id)
    state = (
        ReviewState(
            easiness=row.easiness,
            interval_days=row.interval_days,
            repetitions=row.repetitions,
            due_on=row.due_on,
            last_quality=row.last_quality,
            last_reviewed_on=row.last_reviewed_on,
        )
        if row
        else ReviewState()
    )
    updated = schedule_after_review(state, score, today)
    if row is None:
        row = ReviewScheduleRow(track_id=item.track_id, subtopic_id=item.subtopic_id)
        session.add(row)
    row.easiness = updated.easiness
    row.interval_days = updated.interval_days
    row.repetitions = updated.repetitions
    row.due_on = updated.due_on
    row.last_quality = updated.last_quality
    row.last_reviewed_on = updated.last_reviewed_on
    session.commit()


def list_schedule(session: Session, track_id: str) -> list[ReviewScheduleRow]:
    query = select(ReviewScheduleRow).where(ReviewScheduleRow.track_id == track_id).order_by(ReviewScheduleRow.due_on)
    return list(session.scalars(query))


def due_reviews(session: Session, track_id: str, today: date | None = None) -> list[ReviewScheduleRow]:
    """Subtopics due today or overdue, most overdue (then lowest quality) first."""
    today = today or date.today()
    due = [row for row in list_schedule(session, track_id) if row.due_on <= today]
    return sorted(due, key=lambda row: (row.due_on, row.last_quality if row.last_quality is not None else 0))


def _get_schedule(session: Session, track_id: str, subtopic_id: str) -> ReviewScheduleRow | None:
    query = select(ReviewScheduleRow).where(
        ReviewScheduleRow.track_id == track_id, ReviewScheduleRow.subtopic_id == subtopic_id
    )
    return session.scalars(query).first()
