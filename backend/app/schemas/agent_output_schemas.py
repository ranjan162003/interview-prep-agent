"""The JSON each agent must reply with. These double as the schema sent to the model."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class GeneratedQuizQuestion(BaseModel):
    question: str = Field(min_length=5)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(description="Why the correct option is right and the others are wrong, in 1-3 sentences.")
    key_point: str = Field(description="The one fact to remember, as a single short sentence.")

    @field_validator("options")
    @classmethod
    def options_must_differ(cls, options: list[str]) -> list[str]:
        if len({option.strip().lower() for option in options}) != len(options):
            raise ValueError("options must all be different")
        return options


class GeneratedQuiz(BaseModel):
    questions: list[GeneratedQuizQuestion] = Field(min_length=1)


class GeneratedConceptLesson(BaseModel):
    title: str = Field(min_length=3, description="Short lesson title.")
    lesson_markdown: str = Field(min_length=80, description="The lesson in simple Markdown, 200-400 words, with one worked example.")
    explain_prompt: str = Field(description="The question the learner answers to explain the idea back in their own words.")
    key_points: list[str] = Field(min_length=3, max_length=6, description="3-5 points a good explanation must cover.")
    common_mistakes: list[str] = Field(default_factory=list, max_length=5)
    reference_answer: str = Field(min_length=40, description="A strong interview-quality answer to explain_prompt.")


class GeneratedTeacherReply(BaseModel):
    reply: str = Field(min_length=1, description="The teacher's answer to the learner's doubt, in simple Markdown.")


class GradedCriterion(BaseModel):
    name: str
    score: int = Field(ge=0, le=5)
    comment: str


class GradedEvidence(BaseModel):
    quote: str = Field(description="Exact words from the learner's answer.")
    comment: str


class GeneratedGrade(BaseModel):
    criteria: list[GradedCriterion] = Field(min_length=1)
    covered_points: list[str] = Field(default_factory=list)
    missed_points: list[str] = Field(default_factory=list)
    evidence: list[GradedEvidence] = Field(default_factory=list)
    improved_answer: str
    overall_feedback: str


# ---------- coding problems ----------

PYTHON_IDENTIFIER = r"^[A-Za-z_][A-Za-z0-9_]*$"


class GeneratedCodingTest(BaseModel):
    args: list[Any] = Field(description="Positional arguments for the function, as JSON values.")
    expected: Any = Field(description="The exact return value expected, as a JSON value.")


class GeneratedCodingProblem(BaseModel):
    title: str = Field(min_length=3)
    statement_markdown: str = Field(min_length=60, description="Problem statement with 1-2 examples and constraints.")
    function_name: str = Field(pattern=PYTHON_IDENTIFIER)
    starter_code: str = Field(description="Python 3 function signature with a docstring and `pass`.")
    tests: list[GeneratedCodingTest] = Field(min_length=4, max_length=12)
    hints: list[str] = Field(min_length=3, max_length=3, description="Three hints, from a gentle nudge to almost the approach.")
    reference_solution: str
    time_complexity: str
    space_complexity: str
    key_points: list[str] = Field(min_length=2, max_length=4, description="The pattern/insight to remember.")

    @model_validator(mode="after")
    def code_defines_the_function(self) -> GeneratedCodingProblem:
        for label, code in (("starter_code", self.starter_code), ("reference_solution", self.reference_solution)):
            if f"def {self.function_name}(" not in code:
                raise ValueError(f"{label} must define `def {self.function_name}(`")
        return self


class GeneratedCodeReview(BaseModel):
    correctness: str = Field(description="Why the code passes or fails, pointing at the exact lines or cases.")
    time_complexity: str
    space_complexity: str
    complexity_comment: str
    edge_cases_missed: list[str] = Field(default_factory=list)
    style_comments: list[str] = Field(default_factory=list)
    improved_code: str = Field(description="A clean, optimal version of the learner's solution.")
    overall_feedback: str


# ---------- security labs ----------


class GeneratedLabTask(BaseModel):
    question: str
    expected_answer: str
    key_points: list[str] = Field(min_length=1, max_length=4)


class GeneratedSecurityLab(BaseModel):
    title: str = Field(min_length=3)
    scenario_markdown: str = Field(min_length=40, description="The situation, role and goal, in simple Markdown.")
    artifact_type: str = Field(description="log | code | http | email | config | packet | alert")
    artifact: str = Field(min_length=20, description="The raw evidence to analyse, plain text, at most ~40 lines.")
    tasks: list[GeneratedLabTask] = Field(min_length=2, max_length=4)
    key_points: list[str] = Field(min_length=3, max_length=5)
    walkthrough_markdown: str = Field(min_length=60, description="How an expert analyst solves it, step by step.")


class GradedLabTask(BaseModel):
    score: int = Field(ge=0, le=5)
    comment: str
    missed: list[str] = Field(default_factory=list)


class GeneratedLabGrade(BaseModel):
    tasks: list[GradedLabTask] = Field(min_length=1)
    overall_feedback: str


# ---------- mock interview ----------


class GeneratedMockQuestion(BaseModel):
    question: str = Field(min_length=10)
    subtopic_id: str = Field(description="One of the subtopic ids you were given.")
    key_points: list[str] = Field(min_length=2, max_length=5, description="What a strong answer covers.")
    reference_answer: str = Field(min_length=40)


class GeneratedMockQuestions(BaseModel):
    questions: list[GeneratedMockQuestion] = Field(min_length=1)


class GeneratedInterviewerStep(BaseModel):
    action: str = Field(description='"follow_up" to probe deeper, or "move_on" when the answer is complete enough.')
    follow_up_question: str = Field(default="", description="The follow-up question, when action is follow_up.")
    acknowledgement: str = Field(default="", description="A short, neutral interviewer acknowledgement.")


# ---------- coach ----------


class GeneratedCoachStep(BaseModel):
    action: str = Field(description='"tool" to look something up, or "answer" to reply to the learner.')
    tool: str = Field(default="")
    arguments: dict[str, Any] = Field(default_factory=dict)
    answer: str = Field(default="")
