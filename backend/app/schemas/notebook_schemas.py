"""The learning notebook: everything learnt, browsable and exportable."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.core.utc_time import UtcDatetime
from app.learning.item_status import LearningStatus
from app.schemas.practice_schemas import LessonChatMessage


class NotebookEntry(BaseModel):
    item_id: int
    kind: str
    title: str
    track_id: str
    topic_id: str
    topic_name: str
    subtopic_id: str
    subtopic_name: str
    is_review: bool
    status: LearningStatus
    best_score: float | None
    last_score: float | None
    attempts: int
    key_points: list[str]
    has_chat: bool
    created_at: UtcDatetime


class NotebookPage(BaseModel):
    track_id: str
    entries: list[NotebookEntry]
    total: int
    counts_by_kind: dict[str, int]


class NotebookAttempt(BaseModel):
    created_at: UtcDatetime
    score: float
    answer_text: str
    selected_index: int | None
    grade: dict[str, Any] | None


class NotebookItemDetail(NotebookEntry):
    # Kind-specific body: lesson text, quiz options, problem statement, lab evidence…
    content: dict[str, Any]
    reference_answer: str | None
    rubric: dict[str, Any] | None
    history: list[NotebookAttempt]
    chat: list[LessonChatMessage]
