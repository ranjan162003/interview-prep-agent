"""Hands-on task payloads: coding problems and security labs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.learning.item_status import LearningStatus
from app.schemas.agent_output_schemas import GeneratedCodeReview, GradedLabTask
from app.schemas.practice_schemas import AgentChoice, SubtopicRef


class TaskRequest(AgentChoice):
    subtopic_id: str | None = None


# ---------- coding ----------


class CodingTest(BaseModel):
    args: list[Any]
    expected: Any


class CodingProblemOut(BaseModel):
    item_id: int
    subtopic: SubtopicRef
    title: str
    statement_markdown: str
    function_name: str
    starter_code: str
    tests: list[CodingTest]
    # Run in the browser against the tests first, so a test the model got wrong is dropped
    # instead of failing the learner.
    reference_solution: str
    hint_count: int
    hints_used: int


class HintOut(BaseModel):
    level: int
    hint: str
    hints_used: int


class TestOutcome(BaseModel):
    passed: bool
    args: list[Any] = []
    expected: Any = None
    got: Any = None
    error: str | None = None


class CodeSubmission(AgentChoice):
    code: str = Field(min_length=1, max_length=20000)
    # Results of running the (valid) tests in the browser sandbox.
    results: list[TestOutcome] = Field(min_length=1)


class CodeReviewResult(BaseModel):
    item_id: int
    score: float
    status: LearningStatus
    passed: int
    total: int
    hints_used: int
    review: GeneratedCodeReview
    reference_solution: str
    key_points: list[str]


# ---------- security labs ----------


class LabTaskOut(BaseModel):
    question: str


class SecurityLabOut(BaseModel):
    item_id: int
    subtopic: SubtopicRef
    title: str
    scenario_markdown: str
    artifact_type: str
    artifact: str
    tasks: list[LabTaskOut]


class LabSubmission(AgentChoice):
    answers: list[str] = Field(min_length=1, max_length=6)


class LabTaskResult(GradedLabTask):
    question: str
    your_answer: str
    expected_answer: str


class LabResult(BaseModel):
    item_id: int
    score: float
    status: LearningStatus
    tasks: list[LabTaskResult]
    overall_feedback: str
    walkthrough_markdown: str
    key_points: list[str]
