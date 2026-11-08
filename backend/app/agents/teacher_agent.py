"""Teacher: answers the learner's doubts about the lesson they're reading."""
from __future__ import annotations

from app.agents.llm_json import generate_validated_json
from app.agents.prompts.practice_prompts import build_teacher_chat_prompt
from app.agents.providers.base_llm_provider import BaseLlmProvider
from app.schemas.agent_output_schemas import GeneratedTeacherReply
from app.schemas.track_schemas import SubtopicLocation


class TeacherAgent:
    def __init__(self, provider: BaseLlmProvider, model_name: str | None) -> None:
        self._provider = provider
        self._model_name = model_name

    def answer_doubt(
        self,
        location: SubtopicLocation,
        lesson_title: str,
        lesson_markdown: str,
        explain_prompt: str,
        has_answered: bool,
        history: list[tuple[str, str]],
        question: str,
    ) -> str:
        prompt = build_teacher_chat_prompt(
            location, lesson_title, lesson_markdown, explain_prompt, has_answered, history, question
        )
        return generate_validated_json(self._provider, self._model_name, prompt, GeneratedTeacherReply).reply.strip()
