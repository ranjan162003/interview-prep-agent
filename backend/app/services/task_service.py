"""Hands-on tasks: coding problems (tests run in the browser, then an AI code review) and
security labs (analyse evidence, answer tasks, get graded). Both are saved to the notebook."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.providers.llm_provider_registry import get_llm_provider
from app.agents.task_agents import TaskAgent
from app.core.app_exceptions import InvalidRequestError
from app.db.orm_models import AttemptRow, LearningItemRow
from app.db.repositories import learning_item_repository
from app.learning.item_status import LearningItemKind, LearningStatus
from app.schemas.task_schemas import (
    CodeReviewResult,
    CodeSubmission,
    CodingProblemOut,
    CodingTest,
    HintOut,
    LabResult,
    LabSubmission,
    LabTaskOut,
    LabTaskResult,
    SecurityLabOut,
    TaskRequest,
)
from app.schemas.track_schemas import SubtopicLocation
from app.services import review_service
from app.services.practice_service import generate_unique, get_item_of_kind, new_item, resolve_location, subtopic_ref
from app.syllabus.syllabus_loader import locate_subtopic

HINT_PENALTY = 10.0
MAX_TASK_SCORE = 5


def _already_given(
    session: Session, location: SubtopicLocation, kind: LearningItemKind
) -> tuple[list[str], list[str]]:
    items = learning_item_repository.list_items(session, location.track.id, subtopic_id=location.subtopic.id, kind=kind)
    return [item.title for item in items], [item.normalized_text for item in items]


# ---------- coding ----------


def create_coding_problem(session: Session, request: TaskRequest) -> CodingProblemOut:
    location = resolve_location(session, request.subtopic_id)
    titles, seen = _already_given(session, location, LearningItemKind.CODING_PROBLEM)
    agent = TaskAgent(get_llm_provider(request.provider_id), request.model_name)
    problem = generate_unique(
        lambda: agent.generate_coding_problem(location, titles),
        lambda p: f"{p.title} {p.statement_markdown[:300]}",
        seen,
        on_repeat=lambda p: titles.append(p.title),
        what="a problem you've already solved",
    )
    row = new_item(
        location,
        LearningItemKind.CODING_PROBLEM,
        title=problem.title,
        dedupe_text=f"{problem.title} {problem.statement_markdown[:300]}",
        agent=request,
        content={
            "statement_markdown": problem.statement_markdown,
            "function_name": problem.function_name,
            "starter_code": problem.starter_code,
            "tests": [t.model_dump() for t in problem.tests],
            "hints": problem.hints,
            "hints_used": 0,
            "time_complexity": problem.time_complexity,
            "space_complexity": problem.space_complexity,
        },
        reference_answer=problem.reference_solution,
        key_points=problem.key_points,
    )
    learning_item_repository.add_items(session, [row])
    return _coding_out(row, location)


def _coding_out(row: LearningItemRow, location: SubtopicLocation) -> CodingProblemOut:
    return CodingProblemOut(
        item_id=row.id,
        subtopic=subtopic_ref(location),
        title=row.title,
        statement_markdown=row.content["statement_markdown"],
        function_name=row.content["function_name"],
        starter_code=row.content["starter_code"],
        tests=[CodingTest.model_validate(t) for t in row.content["tests"]],
        reference_solution=row.reference_answer or "",
        hint_count=len(row.content["hints"]),
        hints_used=int(row.content.get("hints_used", 0)),
    )


def reveal_hint(session: Session, item_id: int) -> HintOut:
    """Hints come in order, from a nudge to almost the approach. Each one used before submitting costs points."""
    item = get_item_of_kind(session, item_id, LearningItemKind.CODING_PROBLEM)
    hints = item.content["hints"]
    used = int(item.content.get("hints_used", 0))
    if used >= len(hints):
        return HintOut(level=len(hints), hint=hints[-1], hints_used=used)
    if not item.attempts:  # hints after submitting are free
        # Reassign so SQLAlchemy notices the JSON change.
        item.content = {**item.content, "hints_used": used + 1}
        session.commit()
    return HintOut(level=used + 1, hint=hints[used], hints_used=used + 1)


def submit_code(session: Session, item_id: int, submission: CodeSubmission) -> CodeReviewResult:
    item = get_item_of_kind(session, item_id, LearningItemKind.CODING_PROBLEM)
    location = locate_subtopic(item.track_id, item.subtopic_id)
    passed = sum(1 for r in submission.results if r.passed)
    total = len(submission.results)
    failures = [r.model_dump() for r in submission.results if not r.passed]

    agent = TaskAgent(get_llm_provider(submission.provider_id), submission.model_name)
    review = agent.review_code(location, item.content, item.title, submission.code, passed, total, failures)

    # Tests decide correctness; the model only explains. Each hint used costs a little.
    hints_used = int(item.content.get("hints_used", 0))
    score = max(0.0, round(passed / total * 100 - hints_used * HINT_PENALTY, 1))
    learning_item_repository.add_attempt(
        session,
        item,
        AttemptRow(
            answer_text=submission.code,
            score=score,
            grade={
                "passed": passed,
                "total": total,
                "hints_used": hints_used,
                "failures": failures[:5],
                "review": review.model_dump(),
            },
        ),
    )
    review_service.record_outcome(session, item, score)
    return CodeReviewResult(
        item_id=item.id,
        score=score,
        status=LearningStatus(item.status),
        passed=passed,
        total=total,
        hints_used=hints_used,
        review=review,
        reference_solution=item.reference_answer or "",
        key_points=item.key_points,
    )


# ---------- security labs ----------


def create_security_lab(session: Session, request: TaskRequest) -> SecurityLabOut:
    location = resolve_location(session, request.subtopic_id)
    titles, seen = _already_given(session, location, LearningItemKind.SECURITY_LAB)
    agent = TaskAgent(get_llm_provider(request.provider_id), request.model_name)
    lab = generate_unique(
        lambda: agent.generate_security_lab(location, titles),
        lambda candidate: f"{candidate.title} {candidate.artifact[:300]}",
        seen,
        on_repeat=lambda candidate: titles.append(candidate.title),
        what="a lab you've already done",
    )
    row = new_item(
        location,
        LearningItemKind.SECURITY_LAB,
        title=lab.title,
        dedupe_text=f"{lab.title} {lab.artifact[:300]}",
        agent=request,
        content={
            "scenario_markdown": lab.scenario_markdown,
            "artifact_type": lab.artifact_type,
            "artifact": lab.artifact,
            "tasks": [t.model_dump() for t in lab.tasks],
        },
        rubric={"tasks": [t.model_dump() for t in lab.tasks]},
        reference_answer=lab.walkthrough_markdown,
        key_points=lab.key_points,
    )
    learning_item_repository.add_items(session, [row])
    return SecurityLabOut(
        item_id=row.id,
        subtopic=subtopic_ref(location),
        title=lab.title,
        scenario_markdown=lab.scenario_markdown,
        artifact_type=lab.artifact_type,
        artifact=lab.artifact,
        tasks=[LabTaskOut(question=t.question) for t in lab.tasks],
    )


def submit_lab(session: Session, item_id: int, submission: LabSubmission) -> LabResult:
    item = get_item_of_kind(session, item_id, LearningItemKind.SECURITY_LAB)
    tasks = item.content["tasks"]
    if len(submission.answers) != len(tasks):
        raise InvalidRequestError(f"This lab has {len(tasks)} tasks, but {len(submission.answers)} answers were sent.")
    location = locate_subtopic(item.track_id, item.subtopic_id)

    agent = TaskAgent(get_llm_provider(submission.provider_id), submission.model_name)
    grade = agent.grade_lab(location, item.content, submission.answers)
    score = round(sum(t.score for t in grade.tasks) / (len(tasks) * MAX_TASK_SCORE) * 100, 1)

    learning_item_repository.add_attempt(
        session,
        item,
        AttemptRow(answer_text="\n\n".join(submission.answers), score=score, grade=grade.model_dump()),
    )
    review_service.record_outcome(session, item, score)
    return LabResult(
        item_id=item.id,
        score=score,
        status=LearningStatus(item.status),
        tasks=[
            LabTaskResult(**g.model_dump(), question=t["question"], your_answer=a, expected_answer=t["expected_answer"])
            for g, t, a in zip(grade.tasks, tasks, submission.answers)
        ],
        overall_feedback=grade.overall_feedback,
        walkthrough_markdown=item.reference_answer or "",
        key_points=item.key_points,
    )
