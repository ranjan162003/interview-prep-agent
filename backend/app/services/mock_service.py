"""Mock interview: a few questions, each with up to two follow-ups, graded when the
interviewer moves on. Questions are written once at the start (one LLM call), so each
answer costs at most two calls: "follow up or move on?" and, on moving on, the grade.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.grader_agent import GraderAgent, overall_score
from app.agents.interviewer_agent import InterviewerAgent
from app.agents.providers.llm_provider_registry import get_llm_provider
from app.core.app_exceptions import InvalidRequestError, ProviderCallError, ResourceNotFoundError
from app.db.orm_models import AttemptRow, LearningItemRow, MockSessionRow, MockTurnRow
from app.db.repositories import learning_item_repository
from app.learning.duplicate_detector import is_near_duplicate, normalize_text
from app.learning.item_status import LearningItemKind
from app.schemas.agent_output_schemas import GeneratedGrade, GeneratedMockQuestion
from app.schemas.mock_schemas import (
    MockAnswerRequest,
    MockQuestionGrade,
    MockSession,
    MockSessionSummary,
    MockStartRequest,
    MockTurn,
)
from app.schemas.practice_schemas import AgentChoice
from app.schemas.track_schemas import SubtopicLocation
from app.services import practice_service, review_service
from app.services.practice_service import MAX_GENERATION_ROUNDS, new_item
from app.services.profile_service import require_profile
from app.syllabus.syllabus_loader import get_track, iter_subtopics_in_order, locate_subtopic

MAX_FOLLOW_UPS = 2
FALLBACK_TECHNICAL_SUBTOPICS = 6
RECENT_SESSIONS = 20


def _is_behavioural(location: SubtopicLocation) -> bool:
    return "behavioural" in location.topic.name.lower()


def _candidate_subtopics(session: Session, track_id: str, request: MockStartRequest) -> list[SubtopicLocation]:
    locations = iter_subtopics_in_order(track_id)
    behavioural = [loc for loc in locations if _is_behavioural(loc)]
    if request.subtopic_id:
        technical = [locate_subtopic(track_id, request.subtopic_id)]
    else:
        studied = {c.subtopic_id for c in practice_service.get_overview(session).subtopics if c.status != "not_started"}
        technical = [loc for loc in locations if loc.subtopic.id in studied and not _is_behavioural(loc)]
        if not technical:
            technical = [loc for loc in locations if not _is_behavioural(loc)][:FALLBACK_TECHNICAL_SUBTOPICS]
    if request.kind == "behavioural":
        return behavioural
    if request.kind == "technical":
        return technical
    return technical + behavioural


def start_session(session: Session, request: MockStartRequest) -> MockSession:
    track_id = require_profile(session).track_id
    track = get_track(track_id)
    candidates = _candidate_subtopics(session, track_id, request)
    by_id = {loc.subtopic.id: loc for loc in candidates}

    previous = learning_item_repository.list_items(session, track_id, kind=LearningItemKind.MOCK_QUESTION)
    asked = [item.title for item in previous]
    seen = [item.normalized_text for item in previous]

    agent = InterviewerAgent(get_llm_provider(request.provider_id), request.model_name)
    accepted: list[GeneratedMockQuestion] = []
    for _ in range(MAX_GENERATION_ROUNDS):
        missing = request.question_count - len(accepted)
        if missing <= 0:
            break
        written = agent.write_questions(track.name, request.kind, candidates, missing, asked)
        # Look at every question written: a repeat early in the list mustn't hide a fresh one after it.
        for question in written.questions:
            if len(accepted) >= request.question_count:
                break
            normalized = normalize_text(question.question)
            if any(is_near_duplicate(normalized, s) for s in seen):
                asked.append(question.question)
                continue
            accepted.append(question)
            seen.append(normalized)
    if not accepted:
        raise ProviderCallError("The model only wrote questions you've already been asked. Try again.")

    rows = [
        new_item(
            by_id.get(q.subtopic_id, candidates[0]),
            LearningItemKind.MOCK_QUESTION,
            title=q.question,
            dedupe_text=q.question,
            agent=request,
            content={"question": q.question, "mock_kind": request.kind},
            rubric={"key_points": q.key_points},
            reference_answer=q.reference_answer,
            key_points=q.key_points,
        )
        for q in accepted
    ]
    learning_item_repository.add_items(session, rows)

    mock = MockSessionRow(track_id=track_id, kind=request.kind, question_item_ids=[row.id for row in rows])
    mock.turns.append(MockTurnRow(item_id=rows[0].id, role="interviewer", content=rows[0].title))
    session.add(mock)
    session.commit()
    return get_session(session, mock.id)


def answer(session: Session, session_id: int, request: MockAnswerRequest) -> MockSession:
    mock = _get_row(session, session_id)
    if mock.status != "in_progress":
        raise InvalidRequestError("This mock interview has finished. Start a new one.")
    item = _current_item(session, mock)
    mock.turns.append(MockTurnRow(item_id=item.id, role="candidate", content=request.answer.strip()))
    session.commit()

    location = locate_subtopic(item.track_id, item.subtopic_id)
    if mock.follow_ups_asked < MAX_FOLLOW_UPS:
        interviewer = InterviewerAgent(get_llm_provider(request.provider_id), request.model_name)
        step = interviewer.next_step(
            location,
            item.title,
            item.key_points,
            _transcript(mock, item.id),
            follow_ups_left=MAX_FOLLOW_UPS - mock.follow_ups_asked,
        )
        if step.action == "follow_up" and step.follow_up_question.strip():
            content = f"{step.acknowledgement.strip()} {step.follow_up_question.strip()}".strip()
            mock.turns.append(MockTurnRow(item_id=item.id, role="interviewer", content=content))
            mock.follow_ups_asked += 1
            session.commit()
            return get_session(session, mock.id)
        acknowledgement = step.acknowledgement.strip()
    else:
        acknowledgement = "Okay, thanks."

    _grade_question(session, mock, item, request)
    _advance(session, mock, acknowledgement)
    return get_session(session, mock.id)


def end_session(session: Session, session_id: int, agent: AgentChoice) -> MockSession:
    """Stop early. A question already answered is graded; unanswered ones are skipped."""
    mock = _get_row(session, session_id)
    if mock.status == "in_progress":
        item = _current_item(session, mock)
        if any(t.role == "candidate" for t in mock.turns if t.item_id == item.id) and not item.attempts:
            _grade_question(session, mock, item, agent)
        mock.status = "finished"
        session.commit()
    return get_session(session, mock.id)


def _grade_question(session: Session, mock: MockSessionRow, item: LearningItemRow, agent: AgentChoice) -> None:
    transcript = _transcript(mock, item.id)
    dialogue = "\n\n".join(f"{'Interviewer' if r == 'interviewer' else 'Candidate'}: {t}" for r, t in transcript)
    grader = GraderAgent(get_llm_provider(agent.provider_id), agent.model_name)
    grade = grader.grade_explanation(
        locate_subtopic(item.track_id, item.subtopic_id),
        explain_prompt=item.title,
        key_points=item.key_points,
        common_mistakes=[],
        reference_answer=item.reference_answer or "",
        learner_answer=dialogue,
    )
    score = overall_score(grade)
    learning_item_repository.add_attempt(session, item, AttemptRow(answer_text=dialogue, score=score, grade=grade.model_dump()))
    review_service.record_outcome(session, item, score)


def _advance(session: Session, mock: MockSessionRow, acknowledgement: str) -> None:
    mock.current_index += 1
    mock.follow_ups_asked = 0
    if mock.current_index >= len(mock.question_item_ids):
        mock.status = "finished"
        mock.current_index = len(mock.question_item_ids) - 1
    else:
        next_item = _current_item(session, mock)
        lead = acknowledgement or "Okay."
        mock.turns.append(MockTurnRow(item_id=next_item.id, role="interviewer", content=f"{lead} Next question: {next_item.title}"))
    session.commit()


def _transcript(mock: MockSessionRow, item_id: int) -> list[tuple[str, str]]:
    return [(t.role, t.content) for t in mock.turns if t.item_id == item_id]


def _get_row(session: Session, session_id: int) -> MockSessionRow:
    mock = session.get(MockSessionRow, session_id)
    if mock is None or mock.track_id != require_profile(session).track_id:
        raise ResourceNotFoundError(f"Mock interview {session_id} doesn't exist.")
    return mock


def _current_item(session: Session, mock: MockSessionRow) -> LearningItemRow:
    item = learning_item_repository.get_item(session, mock.question_item_ids[mock.current_index])
    if item is None:
        raise ResourceNotFoundError("This mock interview's question was deleted.")
    return item


def get_session(session: Session, session_id: int) -> MockSession:
    mock = _get_row(session, session_id)
    index_of = {item_id: index for index, item_id in enumerate(mock.question_item_ids)}
    grades: list[MockQuestionGrade] = []
    for index, item_id in enumerate(mock.question_item_ids):
        item = learning_item_repository.get_item(session, item_id)
        if item is None or not item.attempts or not item.attempts[-1].grade:
            continue
        grade = GeneratedGrade.model_validate(item.attempts[-1].grade)
        grades.append(
            MockQuestionGrade(
                question_index=index,
                item_id=item.id,
                question=item.title,
                subtopic_name=locate_subtopic(item.track_id, item.subtopic_id).subtopic.name,
                score=item.attempts[-1].score,
                criteria=grade.criteria,
                covered_points=grade.covered_points,
                missed_points=grade.missed_points,
                improved_answer=grade.improved_answer,
                overall_feedback=grade.overall_feedback,
            )
        )
    return MockSession(
        id=mock.id,
        kind=mock.kind,
        status=mock.status,
        question_count=len(mock.question_item_ids),
        current_index=mock.current_index,
        turns=[
            MockTurn(role=t.role, content=t.content, question_index=index_of.get(t.item_id, 0), created_at=t.created_at)
            for t in mock.turns
        ],
        grades=grades,
        overall_score=round(sum(g.score for g in grades) / len(grades), 1) if grades else None,
        created_at=mock.created_at,
    )


def list_sessions(session: Session) -> list[MockSessionSummary]:
    track_id = require_profile(session).track_id
    query = (
        select(MockSessionRow)
        .where(MockSessionRow.track_id == track_id)
        .order_by(MockSessionRow.created_at.desc())
        .limit(RECENT_SESSIONS)
    )
    summaries = []
    for mock in session.scalars(query):
        full = get_session(session, mock.id)
        summaries.append(
            MockSessionSummary(
                id=mock.id,
                kind=mock.kind,
                status=mock.status,
                question_count=full.question_count,
                overall_score=full.overall_score,
                first_question=full.turns[0].content if full.turns else "",
                created_at=mock.created_at,
            )
        )
    return summaries
