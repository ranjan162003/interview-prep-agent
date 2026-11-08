"""Progress: streak, activity, topic mastery and interview readiness."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.progress_schemas import ProgressOut
from app.services import progress_service

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=ProgressOut)
def read_progress(session: Session = Depends(get_db_session)) -> ProgressOut:
    return progress_service.get_progress(session)
