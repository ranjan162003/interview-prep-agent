"""Coach chat: conversations saved per track, answered by the tool-loop coach agent."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.coach_agent import run_coach_turn
from app.agents.prompts.coach_prompts import build_coach_prompt
from app.agents.providers.llm_provider_registry import get_llm_provider
from app.core.app_exceptions import ResourceNotFoundError
from app.db.orm_models import CoachConversationRow, CoachMessageRow
from app.schemas.coach_schemas import (
    CoachConversation,
    CoachConversationSummary,
    CoachMessage,
    CoachMessageRequest,
    CoachReply,
)
from app.services.coach_tools import COACH_TOOLS, run_coach_tool
from app.services.profile_service import require_profile

TITLE_LENGTH = 60


def send_message(session: Session, request: CoachMessageRequest) -> CoachReply:
    profile = require_profile(session)
    text = request.message.strip()
    conversation = (
        _get_conversation(session, request.conversation_id)
        if request.conversation_id is not None
        else CoachConversationRow(track_id=profile.track_id, title=_title_from(text))
    )
    history = [(m.role, m.content) for m in conversation.messages]
    tools = [(t.name, t.description, t.arguments) for t in COACH_TOOLS.values()]

    outcome = run_coach_turn(
        get_llm_provider(request.provider_id),
        request.model_name,
        build_prompt=lambda steps, must_answer: build_coach_prompt(
            profile.track_name, profile.days_until_interview, tools, history, text, steps, must_answer
        ),
        run_tool=lambda name, arguments: run_coach_tool(session, name, arguments),
        status_text=lambda name: COACH_TOOLS[name].status_text if name in COACH_TOOLS else name,
    )

    # Saved only after the coach answered, so a failed call leaves nothing half-written.
    asked = CoachMessageRow(role="user", content=text, tools_used=[])
    answered = CoachMessageRow(role="assistant", content=outcome.answer, tools_used=outcome.tools_used)
    conversation.messages.extend([asked, answered])
    session.add(conversation)
    session.commit()
    return CoachReply(conversation=_summary(conversation), messages=[_message(asked), _message(answered)])


def list_conversations(session: Session) -> list[CoachConversationSummary]:
    track_id = require_profile(session).track_id
    query = (
        select(CoachConversationRow)
        .where(CoachConversationRow.track_id == track_id)
        .order_by(CoachConversationRow.updated_at.desc())
    )
    return [_summary(row) for row in session.scalars(query)]


def get_conversation(session: Session, conversation_id: int) -> CoachConversation:
    row = _get_conversation(session, conversation_id)
    return CoachConversation(**_summary(row).model_dump(), messages=[_message(m) for m in row.messages])


def delete_conversation(session: Session, conversation_id: int) -> None:
    session.delete(_get_conversation(session, conversation_id))
    session.commit()


def _get_conversation(session: Session, conversation_id: int) -> CoachConversationRow:
    row = session.get(CoachConversationRow, conversation_id)
    if row is None:
        raise ResourceNotFoundError(f"Conversation {conversation_id} doesn't exist.")
    return row


def _title_from(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= TITLE_LENGTH else flat[: TITLE_LENGTH - 1] + "…"


def _summary(row: CoachConversationRow) -> CoachConversationSummary:
    return CoachConversationSummary(id=row.id, title=row.title, updated_at=row.updated_at)


def _message(row: CoachMessageRow) -> CoachMessage:
    return CoachMessage(id=row.id, role=row.role, content=row.content, tools_used=row.tools_used or [], created_at=row.created_at)
