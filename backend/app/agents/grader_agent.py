"""Grader: scores an explain-back answer against the item's saved rubric, and says why."""
from __future__ import annotations

from app.agents.llm_json import generate_validated_json
from app.agents.prompts.practice_prompts import build_explanation_grading_prompt
from app.agents.providers.base_llm_provider import BaseLlmProvider
from app.schemas.agent_output_schemas import GeneratedGrade
from app.schemas.track_schemas import SubtopicLocation

MAX_CRITERION_SCORE = 5


class GraderAgent:
    def __init__(self, provider: BaseLlmProvider, model_name: str | None) -> None:
        self._provider = provider
        self._model_name = model_name

    def grade_explanation(
        self,
        location: SubtopicLocation,
        explain_prompt: str,
        key_points: list[str],
        common_mistakes: list[str],
        reference_answer: str,
        learner_answer: str,
    ) -> GeneratedGrade:
        prompt = build_explanation_grading_prompt(
            location, explain_prompt, key_points, common_mistakes, reference_answer, learner_answer
        )
        return generate_validated_json(self._provider, self._model_name, prompt, GeneratedGrade)


def overall_score(grade: GeneratedGrade) -> float:
    """Average of the criteria, as 0–100. Computed here, not trusted from the model."""
    total = sum(criterion.score for criterion in grade.criteria)
    return round(total / (len(grade.criteria) * MAX_CRITERION_SCORE) * 100, 1)
