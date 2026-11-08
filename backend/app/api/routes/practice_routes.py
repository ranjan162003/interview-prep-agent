"""Practice endpoints: quizzes, concept explain-back (+ teacher chat), coding problems, security labs.

Generation and grading call an LLM and can take a while; FastAPI runs these
plain `def` handlers in its thread pool so other requests aren't blocked.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.practice_schemas import (
    ConceptLessonOut,
    ConceptRequest,
    ExplainRequest,
    ExplainResult,
    LessonChatMessage,
    LessonChatRequest,
    PracticeOverview,
    QuizAnswerRequest,
    QuizAnswerResult,
    QuizRequest,
    QuizSet,
)
from app.schemas.task_schemas import (
    CodeReviewResult,
    CodeSubmission,
    CodingProblemOut,
    HintOut,
    LabResult,
    LabSubmission,
    SecurityLabOut,
    TaskRequest,
)
from app.services import lesson_chat_service, practice_service, task_service

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/overview", response_model=PracticeOverview)
def read_overview(session: Session = Depends(get_db_session)) -> PracticeOverview:
    return practice_service.get_overview(session)


@router.post("/quiz", response_model=QuizSet)
def create_quiz(body: QuizRequest, session: Session = Depends(get_db_session)) -> QuizSet:
    return practice_service.create_quiz(session, body)


@router.post("/quiz/{item_id}/answer", response_model=QuizAnswerResult)
def answer_quiz_question(
    item_id: int, body: QuizAnswerRequest, session: Session = Depends(get_db_session)
) -> QuizAnswerResult:
    return practice_service.answer_quiz_question(session, item_id, body)


@router.post("/concept", response_model=ConceptLessonOut)
def create_concept_lesson(body: ConceptRequest, session: Session = Depends(get_db_session)) -> ConceptLessonOut:
    return practice_service.create_concept_lesson(session, body)


@router.post("/concept/{item_id}/explain", response_model=ExplainResult)
def grade_explanation(item_id: int, body: ExplainRequest, session: Session = Depends(get_db_session)) -> ExplainResult:
    return practice_service.grade_explanation(session, item_id, body)


@router.get("/concept/{item_id}/chat", response_model=list[LessonChatMessage])
def read_lesson_chat(item_id: int, session: Session = Depends(get_db_session)) -> list[LessonChatMessage]:
    return lesson_chat_service.get_history(session, item_id)


@router.post("/concept/{item_id}/chat", response_model=list[LessonChatMessage])
def ask_teacher(
    item_id: int, body: LessonChatRequest, session: Session = Depends(get_db_session)
) -> list[LessonChatMessage]:
    """Ask the teacher a doubt about this lesson; returns the saved question and reply."""
    return lesson_chat_service.ask_teacher(session, item_id, body)


@router.post("/coding", response_model=CodingProblemOut)
def create_coding_problem(body: TaskRequest, session: Session = Depends(get_db_session)) -> CodingProblemOut:
    return task_service.create_coding_problem(session, body)


@router.post("/coding/{item_id}/hint", response_model=HintOut)
def reveal_hint(item_id: int, session: Session = Depends(get_db_session)) -> HintOut:
    return task_service.reveal_hint(session, item_id)


@router.post("/coding/{item_id}/submit", response_model=CodeReviewResult)
def submit_code(item_id: int, body: CodeSubmission, session: Session = Depends(get_db_session)) -> CodeReviewResult:
    return task_service.submit_code(session, item_id, body)


@router.post("/lab", response_model=SecurityLabOut)
def create_security_lab(body: TaskRequest, session: Session = Depends(get_db_session)) -> SecurityLabOut:
    return task_service.create_security_lab(session, body)


@router.post("/lab/{item_id}/submit", response_model=LabResult)
def submit_lab(item_id: int, body: LabSubmission, session: Session = Depends(get_db_session)) -> LabResult:
    return task_service.submit_lab(session, item_id, body)
