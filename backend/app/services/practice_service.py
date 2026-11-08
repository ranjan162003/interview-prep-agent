"""Practice: warm-up quizzes and concept explain-back, saved to the learning notebook.

Every generated question/lesson goes through the no-repeat rule before it is
shown: anything matching what the learner has already seen is thrown away and
regenerated. Every item and answer is saved, so the notebook (and its PDF) has
everything learnt to date.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.orm import Session

from app.agents.grader_agent import GraderAgent, overall_score
from app.agents.providers.llm_provider_registry import get_llm_provider
from app.agents.question_generator_agent import QuestionGeneratorAgent
from app.core.app_exceptions import InvalidRequestError, ProviderCallError, ResourceNotFoundError
from app.db.orm_models import AttemptRow, LearningItemRow
from app.db.repositories import learning_item_repository
from app.learning.duplicate_detector import fingerprint, is_near_duplicate, normalize_text
from app.learning.item_status import LearningItemKind, LearningStatus
from app.schemas.agent_output_schemas import GeneratedQuizQuestion
from app.schemas.practice_schemas import (
    AgentChoice,
    ConceptLessonOut,
    ConceptRequest,
    CoverageStatus,
    ExplainRequest,
    ExplainResult,
    PracticeOverview,
    QuizAnswerRequest,
    QuizAnswerResult,
    QuizQuestionOut,
    QuizRequest,
    QuizSet,
    SubtopicCoverage,
    SubtopicRef,
)
from app.schemas.track_schemas import SubtopicLocation
from app.services import review_service
from app.services.profile_service import require_profile
from app.syllabus.syllabus_loader import iter_subtopics_in_order, locate_subtopic

logger = logging.getLogger(__name__)

T = TypeVar("T")

# First try plus up to two regenerations when the model repeats earlier material.
MAX_GENERATION_ROUNDS = 3


# ---------- coverage / what's next ----------


def get_overview(session: Session) -> PracticeOverview:
    track_id = require_profile(session).track_id
    items = learning_item_repository.list_items(session, track_id)
    coverage = [_subtopic_coverage(location, items) for location in iter_subtopics_in_order(track_id)]
    next_subtopic = next((c.subtopic_id for c in coverage if c.status != "covered"), None)
    return PracticeOverview(track_id=track_id, next_subtopic_id=next_subtopic, subtopics=coverage)


def _subtopic_coverage(location: SubtopicLocation, all_items: list[LearningItemRow]) -> SubtopicCoverage:
    items = [item for item in all_items if item.subtopic_id == location.subtopic.id]
    quiz_items = [item for item in items if item.kind == LearningItemKind.QUIZ_QUESTION and item.attempts]
    taught = _concepts_taught(items)
    key_concept_count = len(location.subtopic.key_concepts)

    status: CoverageStatus
    if any(item.status == LearningStatus.WEAK for item in items):
        status = "weak"
    elif key_concept_count and len(taught) >= key_concept_count:
        status = "covered"
    elif items:
        status = "in_progress"
    else:
        status = "not_started"

    return SubtopicCoverage(
        topic_id=location.topic.id,
        subtopic_id=location.subtopic.id,
        concepts_taught=len(taught),
        key_concept_count=key_concept_count,
        quiz_answered=len(quiz_items),
        quiz_correct=sum(1 for item in quiz_items if (item.attempts[0].score or 0) >= 100),
        status=status,
    )


def _concepts_taught(items: list[LearningItemRow]) -> set[str]:
    return {
        str(item.content.get("focus_concept"))
        for item in items
        if item.kind == LearningItemKind.CONCEPT and not item.is_review
    }


def resolve_location(session: Session, subtopic_id: str | None) -> SubtopicLocation:
    track_id = require_profile(session).track_id
    if subtopic_id:
        return locate_subtopic(track_id, subtopic_id)
    next_id = get_overview(session).next_subtopic_id
    if next_id is None:
        # Everything covered: keep practising from the start of the syllabus.
        return iter_subtopics_in_order(track_id)[0]
    return locate_subtopic(track_id, next_id)


def subtopic_ref(location: SubtopicLocation) -> SubtopicRef:
    return SubtopicRef(
        track_id=location.track.id,
        topic_id=location.topic.id,
        topic_name=location.topic.name,
        subtopic_id=location.subtopic.id,
        subtopic_name=location.subtopic.name,
        difficulty=location.subtopic.difficulty,
    )


def new_item(
    location: SubtopicLocation,
    kind: LearningItemKind,
    title: str,
    dedupe_text: str,
    agent: AgentChoice,
    **fields,
) -> LearningItemRow:
    return LearningItemRow(
        track_id=location.track.id,
        topic_id=location.topic.id,
        subtopic_id=location.subtopic.id,
        kind=kind.value,
        difficulty=location.subtopic.difficulty,
        title=title[:500],
        fingerprint=fingerprint(dedupe_text),
        normalized_text=normalize_text(dedupe_text),
        status=LearningStatus.NEW.value,
        provider_id=agent.provider_id.value,
        model_name=agent.model_name,
        **fields,
    )


# ---------- quiz ----------


def create_quiz(session: Session, request: QuizRequest) -> QuizSet:
    location = resolve_location(session, request.subtopic_id)
    agent = QuestionGeneratorAgent(get_llm_provider(request.provider_id), request.model_name)

    existing = learning_item_repository.list_items(session, location.track.id, kind=LearningItemKind.QUIZ_QUESTION)
    seen_normalized = [item.normalized_text for item in existing]
    asked_in_subtopic = [item.title for item in existing if item.subtopic_id == location.subtopic.id]

    accepted: list[GeneratedQuizQuestion] = []
    duplicates_skipped = 0
    for _ in range(MAX_GENERATION_ROUNDS):
        missing = request.question_count - len(accepted)
        if missing <= 0:
            break
        generated = agent.generate_quiz(location, missing, asked_in_subtopic + [q.question for q in accepted])
        # Look at every question written: a repeat early in the list mustn't hide a fresh one after it.
        for question in generated:
            if len(accepted) >= request.question_count:
                break
            normalized = normalize_text(question.question)
            if any(is_near_duplicate(normalized, seen) for seen in seen_normalized):
                duplicates_skipped += 1
                asked_in_subtopic.append(question.question)  # show the model what it repeated
                continue
            accepted.append(question)
            seen_normalized.append(normalized)

    if not accepted:
        raise ProviderCallError(
            "The model only produced questions you've already answered. Try another subtopic or a different model."
        )
    if duplicates_skipped:
        logger.info("Quiz on %s: skipped %d repeated question(s)", location.subtopic.id, duplicates_skipped)

    rows = [
        new_item(
            location,
            LearningItemKind.QUIZ_QUESTION,
            title=question.question,
            dedupe_text=question.question,
            agent=request,
            content={
                "question": question.question,
                "options": question.options,
                "correct_index": question.correct_index,
                "explanation": question.explanation,
            },
            reference_answer=question.options[question.correct_index],
            key_points=[question.key_point],
        )
        for question in accepted
    ]
    learning_item_repository.add_items(session, rows)
    return QuizSet(
        subtopic=subtopic_ref(location),
        questions=[QuizQuestionOut(item_id=row.id, question=row.content["question"], options=row.content["options"]) for row in rows],
        duplicates_skipped=duplicates_skipped,
    )


def answer_quiz_question(session: Session, item_id: int, request: QuizAnswerRequest) -> QuizAnswerResult:
    item = get_item_of_kind(session, item_id, LearningItemKind.QUIZ_QUESTION)
    correct_index = int(item.content["correct_index"])

    # The first answer counts; asking again just shows the same result (no retrying after the reveal).
    if item.attempts:
        selected = item.attempts[0].selected_index
        selected = request.selected_index if selected is None else selected
    else:
        selected = request.selected_index
        score = 100.0 if selected == correct_index else 0.0
        learning_item_repository.add_attempt(
            session, item, AttemptRow(answer_text=item.content["options"][selected], selected_index=selected, score=score)
        )
        review_service.record_outcome(session, item, score)

    return QuizAnswerResult(
        item_id=item.id,
        selected_index=selected,
        correct=selected == correct_index,
        correct_index=correct_index,
        explanation=str(item.content.get("explanation", "")),
        key_point=item.key_points[0] if item.key_points else "",
        status=LearningStatus(item.status),
    )


# ---------- concept explain-back ----------


def create_concept_lesson(session: Session, request: ConceptRequest) -> ConceptLessonOut:
    location = resolve_location(session, request.subtopic_id)
    concept_items = learning_item_repository.list_items(
        session, location.track.id, subtopic_id=location.subtopic.id, kind=LearningItemKind.CONCEPT
    )
    focus_concept, is_review = _choose_focus_concept(location, concept_items)
    already_taught = [f"{item.title} — asked: {item.content.get('explain_prompt', '')}" for item in concept_items]
    seen_normalized = [item.normalized_text for item in concept_items]

    agent = QuestionGeneratorAgent(get_llm_provider(request.provider_id), request.model_name)
    lesson = generate_unique(
        lambda: agent.generate_concept_lesson(location, focus_concept, is_review, already_taught),
        lambda candidate: f"{candidate.title} {candidate.explain_prompt}",
        seen_normalized,
        on_repeat=lambda candidate: already_taught.append(f"{candidate.title} — asked: {candidate.explain_prompt}"),
        what="a lesson you've already had",
    )

    row = new_item(
        location,
        LearningItemKind.CONCEPT,
        title=lesson.title,
        dedupe_text=f"{lesson.title} {lesson.explain_prompt}",
        agent=request,
        is_review=is_review,
        content={
            "focus_concept": focus_concept,
            "lesson_markdown": lesson.lesson_markdown,
            "explain_prompt": lesson.explain_prompt,
        },
        rubric={"key_points": lesson.key_points, "common_mistakes": lesson.common_mistakes},
        reference_answer=lesson.reference_answer,
        key_points=lesson.key_points,
    )
    learning_item_repository.add_items(session, [row])
    return ConceptLessonOut(
        item_id=row.id,
        subtopic=subtopic_ref(location),
        focus_concept=focus_concept,
        is_review=is_review,
        title=lesson.title,
        lesson_markdown=lesson.lesson_markdown,
        explain_prompt=lesson.explain_prompt,
    )


def _choose_focus_concept(location: SubtopicLocation, concept_items: list[LearningItemRow]) -> tuple[str, bool]:
    """The next key concept not taught yet; once all are taught, review the weakest one.

    Chosen here, not by the model, so the syllabus is followed in order and a
    learnt concept is never taught again as new.
    """
    taught = _concepts_taught(concept_items)
    for concept in location.subtopic.key_concepts:
        if concept not in taught:
            return concept, False

    def review_priority(concept: str) -> tuple[float, int]:
        scores = [item.best_score or 0.0 for item in concept_items if item.content.get("focus_concept") == concept]
        times_seen = len(scores)
        return (min(scores) if scores else 0.0, times_seen)

    return min(location.subtopic.key_concepts, key=review_priority), True


def grade_explanation(session: Session, item_id: int, request: ExplainRequest) -> ExplainResult:
    item = get_item_of_kind(session, item_id, LearningItemKind.CONCEPT)
    location = locate_subtopic(item.track_id, item.subtopic_id)
    rubric = item.rubric or {}

    grader = GraderAgent(get_llm_provider(request.provider_id), request.model_name)
    grade = grader.grade_explanation(
        location,
        explain_prompt=str(item.content.get("explain_prompt", "")),
        key_points=list(rubric.get("key_points") or item.key_points),
        common_mistakes=list(rubric.get("common_mistakes") or []),
        reference_answer=item.reference_answer or "",
        learner_answer=request.answer.strip(),
    )
    score = overall_score(grade)

    attempt = learning_item_repository.add_attempt(
        session, item, AttemptRow(answer_text=request.answer.strip(), score=score, grade=grade.model_dump())
    )
    # Status follows the latest answer (a retry after feedback can lift a weak item); the best score is kept.
    review_service.record_outcome(session, item, score)

    return ExplainResult(
        item_id=item.id,
        attempt_id=attempt.id,
        score=score,
        status=LearningStatus(item.status),
        criteria=grade.criteria,
        covered_points=grade.covered_points,
        missed_points=grade.missed_points,
        evidence=grade.evidence,
        improved_answer=grade.improved_answer,
        overall_feedback=grade.overall_feedback,
        key_points=item.key_points,
        reference_answer=item.reference_answer or "",
    )


def generate_unique(
    generate: Callable[[], T],
    dedupe_text: Callable[[T], str],
    seen_normalized: list[str],
    on_repeat: Callable[[T], None],
    what: str,
) -> T:
    """Call `generate` until it returns something the learner hasn't seen (the no-repeat rule)."""
    for _ in range(MAX_GENERATION_ROUNDS):
        candidate = generate()
        if not any(is_near_duplicate(normalize_text(dedupe_text(candidate)), seen) for seen in seen_normalized):
            return candidate
        on_repeat(candidate)
    raise ProviderCallError(f"The model kept repeating {what}. Try again, or pick a different model.")


def get_item_of_kind(session: Session, item_id: int, kind: LearningItemKind) -> LearningItemRow:
    item = learning_item_repository.get_item(session, item_id)
    if item is None:
        raise ResourceNotFoundError(f"Learning item {item_id} doesn't exist.")
    if item.kind != kind.value:
        raise InvalidRequestError(f"Item {item_id} is a {item.kind}, not a {kind.value}.")
    return item
