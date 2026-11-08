"""Agents for hands-on tasks: coding problems + code review, security labs + lab grading."""
from __future__ import annotations

from app.agents.llm_json import generate_validated_json
from app.agents.prompts.task_prompts import (
    build_code_review_prompt,
    build_coding_problem_prompt,
    build_lab_grading_prompt,
    build_security_lab_prompt,
)
from app.agents.providers.base_llm_provider import BaseLlmProvider
from app.core.app_exceptions import AgentResponseParseError
from app.schemas.agent_output_schemas import (
    GeneratedCodeReview,
    GeneratedCodingProblem,
    GeneratedLabGrade,
    GeneratedSecurityLab,
)
from app.schemas.track_schemas import SubtopicLocation


class TaskAgent:
    def __init__(self, provider: BaseLlmProvider, model_name: str | None) -> None:
        self._provider = provider
        self._model_name = model_name

    def _ask(self, prompt: str, response_model):
        return generate_validated_json(self._provider, self._model_name, prompt, response_model)

    def generate_coding_problem(self, location: SubtopicLocation, already_given: list[str]) -> GeneratedCodingProblem:
        return self._ask(build_coding_problem_prompt(location, already_given), GeneratedCodingProblem)

    def review_code(
        self,
        location: SubtopicLocation,
        problem: dict,
        title: str,
        code: str,
        passed: int,
        total: int,
        failures: list[dict],
    ) -> GeneratedCodeReview:
        prompt = build_code_review_prompt(
            location,
            title,
            problem["statement_markdown"],
            problem["time_complexity"],
            problem["space_complexity"],
            code,
            passed,
            total,
            failures,
        )
        return self._ask(prompt, GeneratedCodeReview)

    def generate_security_lab(self, location: SubtopicLocation, already_given: list[str]) -> GeneratedSecurityLab:
        return self._ask(build_security_lab_prompt(location, already_given), GeneratedSecurityLab)

    def grade_lab(self, location: SubtopicLocation, lab: dict, answers: list[str]) -> GeneratedLabGrade:
        prompt = build_lab_grading_prompt(location, lab["scenario_markdown"], lab["artifact"], lab["tasks"], answers)
        grade = self._ask(prompt, GeneratedLabGrade)
        if len(grade.tasks) != len(lab["tasks"]):
            raise AgentResponseParseError(
                f"The grader scored {len(grade.tasks)} tasks but the lab has {len(lab['tasks'])}. Try again."
            )
        return grade
