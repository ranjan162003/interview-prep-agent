"""Read-only tools the coach can call to answer questions about the learner's own prep."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.app_exceptions import InvalidRequestError
from app.learning.item_status import LearningStatus
from app.services import notebook_service, progress_service
from app.services.notebook_service import NotebookFilters

MAX_RESULT_CHARS = 3500
MAX_SEARCH_RESULTS = 6
MAX_TEXT_CHARS = 600


@dataclass(frozen=True)
class CoachTool:
    name: str
    description: str
    arguments: str
    status_text: str
    run: Callable[[Session, dict[str, Any]], Any]


def _short(text: str | None, limit: int = MAX_TEXT_CHARS) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _progress(session: Session, _: dict[str, Any]) -> dict[str, Any]:
    p = progress_service.get_progress(session)
    return {
        "track": p.track_name,
        "days_until_interview": p.days_until_interview,
        "streak_days": p.streak_days,
        "minutes_this_week": p.minutes_this_week,
        "items_learnt": p.items_learnt,
        "answers_total": p.answers_total,
        "average_recent_score": p.average_recent_score,
        "reviews_due_today": p.reviews_due,
        "readiness": p.readiness.model_dump(),
        "topics": [
            {"topic": t.name, "mastery": t.mastery, "coverage_percent": round(t.coverage * 100)} for t in p.topics
        ],
    }


def _weak_spots(session: Session, _: dict[str, Any]) -> dict[str, Any]:
    p = progress_service.get_progress(session)
    weak_subtopics = [
        {"topic": t.name, "subtopic": s.name, "mastery": s.mastery, "next_review_on": str(s.next_review_on)}
        for t in p.topics
        for s in t.subtopics
        if s.status == "weak"
    ]
    weak_items = notebook_service.list_entries(session, NotebookFilters(status=LearningStatus.WEAK.value)).entries
    return {
        "weak_subtopics": weak_subtopics,
        "recent_weak_items": [
            {"item_id": e.item_id, "kind": e.kind, "title": e.title, "subtopic": e.subtopic_name, "last_score": e.last_score}
            for e in weak_items[:MAX_SEARCH_RESULTS]
        ],
    }


def _syllabus(session: Session, args: dict[str, Any]) -> dict[str, Any]:
    topic_filter = str(args.get("topic") or "").strip().lower()
    p = progress_service.get_progress(session)
    topics = [t for t in p.topics if not topic_filter or topic_filter in t.name.lower() or topic_filter == t.topic_id]
    return {
        "topics": [
            {
                "topic": t.name,
                "subtopics": [
                    {"subtopic": s.name, "status": s.status, "coverage_percent": round(s.coverage * 100), "mastery": s.mastery}
                    for s in t.subtopics
                ],
            }
            for t in topics
        ]
    }


def _search_notebook(session: Session, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        raise InvalidRequestError("search_notebook needs a 'query'.")
    entries = notebook_service.list_entries(session, NotebookFilters(query=query)).entries[:MAX_SEARCH_RESULTS]
    return {
        "results": [
            {
                "item_id": e.item_id,
                "kind": e.kind,
                "title": e.title,
                "subtopic": e.subtopic_name,
                "status": e.status,
                "last_score": e.last_score,
                "key_points": e.key_points,
            }
            for e in entries
        ]
    }


def _notebook_item(session: Session, args: dict[str, Any]) -> dict[str, Any]:
    try:
        item_id = int(args.get("item_id"))
    except (TypeError, ValueError) as exc:
        raise InvalidRequestError("get_notebook_item needs a numeric 'item_id'.") from exc
    detail = notebook_service.get_detail(session, item_id)
    last = detail.history[-1] if detail.history else None
    grade = (last.grade or {}) if last else {}
    return {
        "kind": detail.kind,
        "title": detail.title,
        "subtopic": detail.subtopic_name,
        "question": _short(str(detail.content.get("explain_prompt") or detail.content.get("question") or detail.title)),
        "key_points": detail.key_points,
        "learner_last_answer": _short(last.answer_text if last else None),
        "last_score": last.score if last else None,
        "grader_feedback": _short(str(grade.get("overall_feedback") or (grade.get("review") or {}).get("overall_feedback") or "")),
        "missed_points": grade.get("missed_points", []),
        "model_answer": _short(detail.reference_answer),
    }


COACH_TOOLS: dict[str, CoachTool] = {
    tool.name: tool
    for tool in (
        CoachTool("get_progress", "Streak, readiness score, minutes studied and mastery per topic.", "{}", "Checking your progress…", _progress),
        CoachTool("get_weak_spots", "Subtopics and recent answers the learner scored low on.", "{}", "Looking at your weak spots…", _weak_spots),
        CoachTool("get_syllabus", "Topics and subtopics with status, coverage and mastery.", '{"topic": "optional topic name"}', "Reading the syllabus…", _syllabus),
        CoachTool("search_notebook", "Search everything the learner has studied.", '{"query": "words to search for"}', "Searching your notebook…", _search_notebook),
        CoachTool("get_notebook_item", "One studied item: the question, the learner's answer, the grade and the model answer.", '{"item_id": 12}', "Opening that answer…", _notebook_item),
    )
}


def run_coach_tool(session: Session, name: str, arguments: dict[str, Any]) -> str:
    tool = COACH_TOOLS.get(name)
    if tool is None:
        raise InvalidRequestError(f"There is no tool called '{name}'. Use one of: {', '.join(COACH_TOOLS)}.")
    result = json.dumps(tool.run(session, arguments), default=str, ensure_ascii=False)
    return result if len(result) <= MAX_RESULT_CHARS else result[:MAX_RESULT_CHARS] + "…(truncated)"
