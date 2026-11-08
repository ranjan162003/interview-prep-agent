"""Load the career-track syllabus files in `syllabus/tracks/*.yaml`.

Adding a track is adding a YAML file — no code changes. Files are validated on
load, so a typo (missing field, duplicate subtopic id) fails loudly at startup
instead of mid-session.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.core.app_exceptions import ResourceNotFoundError
from app.schemas.track_schemas import SubtopicLocation, Track, TrackSummary

TRACKS_DIR = Path(__file__).resolve().parent / "tracks"


@lru_cache
def load_all_tracks() -> dict[str, Track]:
    loaded: list[Track] = []
    for path in sorted(TRACKS_DIR.glob("*.yaml")):
        track = Track.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        _check_unique_ids(track, path)
        loaded.append(track)
    return {track.id: track for track in sorted(loaded, key=lambda t: t.position)}


def _check_unique_ids(track: Track, path: Path) -> None:
    seen: set[str] = set()
    for topic in track.topics:
        for subtopic in topic.subtopics:
            if subtopic.id in seen:
                raise ValueError(f"{path.name}: subtopic id '{subtopic.id}' is used more than once")
            seen.add(subtopic.id)


def get_track(track_id: str) -> Track:
    track = load_all_tracks().get(track_id)
    if track is None:
        raise ResourceNotFoundError(f"Unknown track '{track_id}'.")
    return track


def summarize_track(track: Track) -> TrackSummary:
    return TrackSummary(
        id=track.id,
        name=track.name,
        description=track.description,
        has_coding_problems=track.has_coding_problems,
        topic_count=len(track.topics),
        subtopic_count=sum(len(topic.subtopics) for topic in track.topics),
    )


def list_track_summaries() -> list[TrackSummary]:
    return [summarize_track(track) for track in load_all_tracks().values()]


def iter_subtopics_in_order(track_id: str) -> list[SubtopicLocation]:
    """Every subtopic of a track in learning order (the order of the YAML file)."""
    track = get_track(track_id)
    summary = summarize_track(track)
    return [
        SubtopicLocation(track=summary, topic=topic, subtopic=subtopic)
        for topic in track.topics
        for subtopic in topic.subtopics
    ]


def locate_subtopic(track_id: str, subtopic_id: str) -> SubtopicLocation:
    for location in iter_subtopics_in_order(track_id):
        if location.subtopic.id == subtopic_id:
            return location
    raise ResourceNotFoundError(f"Subtopic '{subtopic_id}' isn't part of the '{track_id}' track.")
