"""Interviewer: writes a mock interview's questions and decides when to ask a follow-up."""
from __future__ import annotations

from app.agents.llm_json import generate_validated_json
from app.agents.prompts.mock_prompts import build_interviewer_step_prompt, build_mock_questions_prompt
from app.agents.providers.base_llm_provider import BaseLlmProvider
from app.schemas.agent_output_schemas import GeneratedInterviewerStep, GeneratedMockQuestions
from app.schemas.track_schemas import SubtopicLocation


class InterviewerAgent:
    def __init__(self, provider: BaseLlmProvider, model_name: str | None) -> None:
        self._provider = provider
        self._model_name = model_name

    def write_questions(
        self, track_name: str, kind: str, candidates: list[SubtopicLocation], count: int, already_asked: list[str]
    ) -> GeneratedMockQuestions:
        prompt = build_mock_questions_prompt(track_name, kind, candidates, count, already_asked)
        return generate_validated_json(self._provider, self._model_name, prompt, GeneratedMockQuestions)

    def next_step(
        self,
        location: SubtopicLocation,
        question: str,
        key_points: list[str],
        transcript: list[tuple[str, str]],
        follow_ups_left: int,
    ) -> GeneratedInterviewerStep:
        prompt = build_interviewer_step_prompt(location, question, key_points, transcript, follow_ups_left)
        return generate_validated_json(self._provider, self._model_name, prompt, GeneratedInterviewerStep)
