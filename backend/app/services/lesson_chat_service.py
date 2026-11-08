"""The "Ask the teacher" chat beside each lesson. Every message is saved with the lesson."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.providers.llm_provider_registry import get_llm_provider
from app.agents.teacher_agent import TeacherAgent
from app.db.orm_models import LessonChatMessageRow
from app.learning.item_status import LearningItemKind
from app.schemas.practice_schemas import LessonChatMessage, LessonChatRequest
from app.services.practice_service import get_item_of_kind
from app.syllabus.syllabus_loader import locate_subtopic


def get_history(session: Session, item_id: int) -> list[LessonChatMessage]:
    item = get_item_of_kind(session, item_id, LearningItemKind.CONCEPT)
    return [_to_schema(message) for message in item.chat_messages]


def ask_teacher(session: Session, item_id: int, request: LessonChatRequest) -> list[LessonChatMessage]:
    """Answer one doubt; returns the saved question and reply."""
    item = get_item_of_kind(session, item_id, LearningItemKind.CONCEPT)
    question = request.message.strip()
    teacher = TeacherAgent(get_llm_provider(request.provider_id), request.model_name)
    reply = teacher.answer_doubt(
        locate_subtopic(item.track_id, item.subtopic_id),
        lesson_title=item.title,
        lesson_markdown=str(item.content.get("lesson_markdown", "")),
        explain_prompt=str(item.content.get("explain_prompt", "")),
        has_answered=bool(item.attempts),
        history=[(message.role, message.content) for message in item.chat_messages],
        question=question,
    )

    # Saved only once the teacher has answered, so a failed call leaves no orphan question behind.
    asked = LessonChatMessageRow(role="user", content=question)
    answered = LessonChatMessageRow(role="assistant", content=reply)
    item.chat_messages.extend([asked, answered])
    session.commit()
    return [_to_schema(asked), _to_schema(answered)]


def _to_schema(row: LessonChatMessageRow) -> LessonChatMessage:
    return LessonChatMessage(id=row.id, role=row.role, content=row.content, created_at=row.created_at)
