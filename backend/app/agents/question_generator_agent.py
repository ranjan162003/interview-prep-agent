"""Question generator: fresh quiz questions and concept lessons, grounded in the syllabus."""
from __future__ import annotations

from app.agents.llm_json import generate_validated_json
from app.agents.prompts.practice_prompts import build_concept_lesson_prompt, build_quiz_prompt
from app.agents.providers.base_llm_provider import BaseLlmProvider
from app.schemas.agent_output_schemas import GeneratedConceptLesson, GeneratedQuiz, GeneratedQuizQuestion
from app.schemas.track_schemas import SubtopicLocation


class QuestionGeneratorAgent:
    def __init__(self, provider: BaseLlmProvider, model_name: str | None) -> None:
        self._provider = provider
        self._model_name = model_name

    def generate_quiz(
        self, location: SubtopicLocation, question_count: int, already_asked: list[str]
    ) -> list[GeneratedQuizQuestion]:
        prompt = build_quiz_prompt(location, question_count, already_asked)
        return generate_validated_json(self._provider, self._model_name, prompt, GeneratedQuiz).questions

    def generate_concept_lesson(
        self,
        location: SubtopicLocation,
        focus_concept: str,
        is_review: bool,
        lessons_already_taught: list[str],
    ) -> GeneratedConceptLesson:
        prompt = build_concept_lesson_prompt(location, focus_concept, is_review, lessons_already_taught)
        return generate_validated_json(self._provider, self._model_name, prompt, GeneratedConceptLesson)
