"""The daily plan: an ordered list of timed blocks for today."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.learning.item_status import LearningStatus

BlockKind = Literal["quiz", "concept", "coding", "lab", "mock", "recap"]
MockKind = Literal["technical", "behavioural", "mixed"]


class PlanBlock(BaseModel):
    id: str
    kind: BlockKind
    title: str
    minutes: int
    subtopic_id: str | None = None
    subtopic_name: str | None = None
    topic_name: str | None = None
    # Why the planner chose this block today ("Due for review — you scored 40% on Monday").
    reason: str
    is_review: bool = False
    mock_kind: MockKind | None = None
    done: bool = False


class DailyPlan(BaseModel):
    plan_date: date
    track_id: str
    daily_minutes: int
    blocks: list[PlanBlock]
    minutes_done: int
    days_until_interview: int | None


class RecapItem(BaseModel):
    item_id: int
    kind: str
    title: str
    subtopic_name: str
    score: float | None
    status: LearningStatus
    key_points: list[str]


class DailyRecap(BaseModel):
    plan_date: date
    minutes_done: int
    items: list[RecapItem]
    weak_subtopics: list[str]
    next_up: str | None
    reviews_due_tomorrow: int
