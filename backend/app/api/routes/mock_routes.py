"""Mock interview: start, answer (with follow-ups), finish early, review past sessions."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.mock_schemas import MockAnswerRequest, MockSession, MockSessionSummary, MockStartRequest
from app.schemas.practice_schemas import AgentChoice
from app.services import mock_service

router = APIRouter(prefix="/mock/sessions", tags=["mock interview"])


@router.get("", response_model=list[MockSessionSummary])
def list_sessions(session: Session = Depends(get_db_session)) -> list[MockSessionSummary]:
    return mock_service.list_sessions(session)


@router.post("", response_model=MockSession)
def start_session(body: MockStartRequest, session: Session = Depends(get_db_session)) -> MockSession:
    return mock_service.start_session(session, body)


@router.get("/{session_id}", response_model=MockSession)
def read_session(session_id: int, session: Session = Depends(get_db_session)) -> MockSession:
    return mock_service.get_session(session, session_id)


@router.post("/{session_id}/answer", response_model=MockSession)
def answer(session_id: int, body: MockAnswerRequest, session: Session = Depends(get_db_session)) -> MockSession:
    return mock_service.answer(session, session_id, body)


@router.post("/{session_id}/end", response_model=MockSession)
def end_session(session_id: int, body: AgentChoice, session: Session = Depends(get_db_session)) -> MockSession:
    return mock_service.end_session(session, session_id, body)
