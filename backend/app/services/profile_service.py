"""Read and save the learner's profile (track, interview date, session length)."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.app_exceptions import InvalidRequestError
from app.db.orm_models import UserProfileRow
from app.schemas.profile_schemas import Profile, ProfileUpdate
from app.syllabus.syllabus_loader import get_track

PROFILE_ROW_ID = 1


def get_profile(session: Session) -> Profile | None:
    row = session.get(UserProfileRow, PROFILE_ROW_ID)
    return _to_schema(row) if row else None


def require_profile(session: Session) -> Profile:
    profile = get_profile(session)
    if profile is None:
        raise InvalidRequestError("Pick your career track in Settings first.")
    return profile


def save_profile(session: Session, update: ProfileUpdate) -> Profile:
    get_track(update.track_id)  # unknown track -> 404
    if update.interview_date is not None and update.interview_date < date.today():
        raise InvalidRequestError("The interview date is in the past — pick a future date or 'no date yet'.")

    row = session.get(UserProfileRow, PROFILE_ROW_ID) or UserProfileRow(id=PROFILE_ROW_ID)
    row.track_id = update.track_id
    row.interview_date = update.interview_date
    row.daily_minutes = update.daily_minutes
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_schema(row)


def _to_schema(row: UserProfileRow) -> Profile:
    days_left = (row.interview_date - date.today()).days if row.interview_date else None
    return Profile(
        track_id=row.track_id,
        track_name=get_track(row.track_id).name,
        interview_date=row.interview_date,
        daily_minutes=row.daily_minutes,
        days_until_interview=days_left,
        updated_at=row.updated_at,
    )
