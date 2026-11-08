"""Mock interview payloads."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.utc_time import UtcDatetime
from app.schemas.agent_output_schemas import GradedCriterion
from app.schemas.plan_schemas import MockKind
from app.schemas.practice_schemas import AgentChoice


class MockStartRequest(AgentChoice):
    kind: MockKind = "mixed"
    # Focus every technical question on one subtopic; None = spread over what's been studied.
    subtopic_id: str | None = None
    question_count: int = Field(default=3, ge=1, le=5)


class MockAnswerRequest(AgentChoice):
    answer: str = Field(min_length=1, max_length=6000)


class MockTurn(BaseModel):
    role: Literal["interviewer", "candidate"]
    content: str
    question_index: int
    created_at: UtcDatetime


class MockQuestionGrade(BaseModel):
    question_index: int
    item_id: int
    question: str
    subtopic_name: str
    score: float
    criteria: list[GradedCriterion]
    covered_points: list[str]
    missed_points: list[str]
    improved_answer: str
    overall_feedback: str


class MockSession(BaseModel):
    id: int
    kind: MockKind
    status: Literal["in_progress", "finished"]
    question_count: int
    current_index: int
    turns: list[MockTurn]
    grades: list[MockQuestionGrade]
    overall_score: float | None
    created_at: UtcDatetime


class MockSessionSummary(BaseModel):
    id: int
    kind: MockKind
    status: Literal["in_progress", "finished"]
    question_count: int
    overall_score: float | None
    first_question: str
    created_at: UtcDatetime
