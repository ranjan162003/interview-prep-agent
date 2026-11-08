"""The learner's profile: track, interview date, daily session length."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.profile_schemas import Profile, ProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=Profile | None)
def read_profile(session: Session = Depends(get_db_session)) -> Profile | None:
    """`null` until the learner has picked a track."""
    return profile_service.get_profile(session)


@router.put("", response_model=Profile)
def save_profile(body: ProfileUpdate, session: Session = Depends(get_db_session)) -> Profile:
    return profile_service.save_profile(session, body)
