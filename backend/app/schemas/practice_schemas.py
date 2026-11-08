"""Practice API payloads: warm-up quizzes and concept explain-back."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.utc_time import UtcDatetime
from app.learning.item_status import LearningStatus
from app.schemas.agent_output_schemas import GradedCriterion, GradedEvidence
from app.schemas.provider_schemas import ProviderId


class AgentChoice(BaseModel):
    """Which connected model does the work for this request."""

    provider_id: ProviderId
    model_name: str | None = None


class SubtopicRef(BaseModel):
    track_id: str
    topic_id: str
    topic_name: str
    subtopic_id: str
    subtopic_name: str
    difficulty: int


# ---------- coverage ----------

CoverageStatus = Literal["not_started", "in_progress", "covered", "weak"]


class SubtopicCoverage(BaseModel):
    topic_id: str
    subtopic_id: str
    concepts_taught: int
    key_concept_count: int
    quiz_answered: int
    quiz_correct: int
    status: CoverageStatus


class PracticeOverview(BaseModel):
    track_id: str
    # The first subtopic in syllabus order that isn't fully covered yet.
    next_subtopic_id: str | None
    subtopics: list[SubtopicCoverage]


# ---------- quiz ----------


class QuizRequest(AgentChoice):
    # None = the next subtopic for this learner.
    subtopic_id: str | None = None
    question_count: int = Field(default=5, ge=3, le=10)


class QuizQuestionOut(BaseModel):
    item_id: int
    question: str
    options: list[str]


class QuizSet(BaseModel):
    subtopic: SubtopicRef
    questions: list[QuizQuestionOut]
    # Questions the model wrote that repeated earlier ones and were thrown away.
    duplicates_skipped: int


class QuizAnswerRequest(BaseModel):
    selected_index: int = Field(ge=0, le=3)


class QuizAnswerResult(BaseModel):
    item_id: int
    selected_index: int
    correct: bool
    correct_index: int
    explanation: str
    key_point: str
    status: LearningStatus


# ---------- concept explain-back ----------


class ConceptRequest(AgentChoice):
    subtopic_id: str | None = None


class ConceptLessonOut(BaseModel):
    item_id: int
    subtopic: SubtopicRef
    focus_concept: str
    is_review: bool
    title: str
    lesson_markdown: str
    explain_prompt: str


class LessonChatMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: UtcDatetime


class LessonChatRequest(AgentChoice):
    message: str = Field(min_length=1, max_length=2000)


class ExplainRequest(AgentChoice):
    answer: str = Field(min_length=1, max_length=6000)


class ExplainResult(BaseModel):
    item_id: int
    attempt_id: int
    score: float
    status: LearningStatus
    criteria: list[GradedCriterion]
    covered_points: list[str]
    missed_points: list[str]
    evidence: list[GradedEvidence]
    improved_answer: str
    overall_feedback: str
    # Revealed only after answering: the revision note and the model answer.
    key_points: list[str]
    reference_answer: str
