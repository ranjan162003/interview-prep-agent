"""Progress: streak, activity, topic mastery and interview readiness."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.schemas.practice_schemas import CoverageStatus


class ActivityDay(BaseModel):
    day: date
    answers: int
    minutes: int


class SubtopicMastery(BaseModel):
    subtopic_id: str
    name: str
    difficulty: int
    # Average of the latest scores on this subtopic's items; None until something is answered.
    mastery: float | None
    # Share of the subtopic's key concepts taught (0–1).
    coverage: float
    status: CoverageStatus
    next_review_on: date | None


class TopicMastery(BaseModel):
    topic_id: str
    name: str
    mastery: float | None
    coverage: float
    subtopics: list[SubtopicMastery]


ReadinessLabel = Literal["Getting started", "Building foundations", "Getting there", "Nearly ready", "Interview ready"]


class Readiness(BaseModel):
    score: float
    label: ReadinessLabel
    coverage_percent: float
    mastery_percent: float | None
    mock_average: float | None


class ProgressOut(BaseModel):
    track_id: str
    track_name: str
    days_until_interview: int | None
    streak_days: int
    longest_streak: int
    minutes_total: int
    minutes_this_week: int
    items_seen: int
    items_learnt: int
    answers_total: int
    average_recent_score: float | None
    reviews_due: int
    readiness: Readiness
    activity: list[ActivityDay]
    topics: list[TopicMastery]
