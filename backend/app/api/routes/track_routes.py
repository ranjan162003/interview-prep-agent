"""Career tracks and their syllabus."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.track_schemas import Track, TrackSummary
from app.syllabus.syllabus_loader import get_track, list_track_summaries

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackSummary])
def list_tracks() -> list[TrackSummary]:
    return list_track_summaries()


@router.get("/{track_id}", response_model=Track)
def read_track(track_id: str) -> Track:
    return get_track(track_id)
