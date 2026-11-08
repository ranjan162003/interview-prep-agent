"""Coach chat: ask anything about your prep; the coach can look up your own data."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.coach_schemas import CoachConversation, CoachConversationSummary, CoachMessageRequest, CoachReply
from app.services import coach_service

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/messages", response_model=CoachReply)
def send_message(body: CoachMessageRequest, session: Session = Depends(get_db_session)) -> CoachReply:
    return coach_service.send_message(session, body)


@router.get("/conversations", response_model=list[CoachConversationSummary])
def list_conversations(session: Session = Depends(get_db_session)) -> list[CoachConversationSummary]:
    return coach_service.list_conversations(session)


@router.get("/conversations/{conversation_id}", response_model=CoachConversation)
def read_conversation(conversation_id: int, session: Session = Depends(get_db_session)) -> CoachConversation:
    return coach_service.get_conversation(session, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, session: Session = Depends(get_db_session)) -> None:
    coach_service.delete_conversation(session, conversation_id)
