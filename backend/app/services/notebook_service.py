"""The learning notebook: browse, search and export everything learnt to date."""
from __future__ import annotations

from collections import Counter
from datetime import date

from sqlalchemy.orm import Session

from app.core.app_exceptions import ResourceNotFoundError
from app.db.orm_models import LearningItemRow
from app.db.repositories import learning_item_repository
from app.learning.notebook_pdf_builder import NotebookPdfOptions, build_notebook_pdf
from app.schemas.notebook_schemas import NotebookAttempt, NotebookEntry, NotebookItemDetail, NotebookPage
from app.schemas.practice_schemas import LessonChatMessage
from app.services.profile_service import require_profile
from app.services.progress_service import local_day
from app.syllabus.syllabus_loader import get_track, iter_subtopics_in_order


class NotebookFilters:
    def __init__(
        self,
        track_id: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        topic_id: str | None = None,
        query: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> None:
        self.track_id = track_id
        self.kind = kind
        self.status = status
        self.topic_id = topic_id
        self.query = (query or "").strip().lower()
        self.date_from = date_from
        self.date_to = date_to


def _matches(item: LearningItemRow, filters: NotebookFilters) -> bool:
    if filters.kind and item.kind != filters.kind:
        return False
    if filters.status and item.status != filters.status:
        return False
    if filters.topic_id and item.topic_id != filters.topic_id:
        return False
    created = local_day(item.created_at)
    if filters.date_from and created < filters.date_from:
        return False
    if filters.date_to and created > filters.date_to:
        return False
    if filters.query:
        haystack = " ".join([item.title, *item.key_points, str(item.content.get("explain_prompt", ""))]).lower()
        if filters.query not in haystack:
            return False
    return True


def _filtered_items(session: Session, filters: NotebookFilters) -> tuple[str, list[LearningItemRow]]:
    track_id = filters.track_id or require_profile(session).track_id
    get_track(track_id)  # unknown track -> 404
    items = [i for i in learning_item_repository.list_items(session, track_id) if _matches(i, filters)]
    return track_id, items


def list_entries(session: Session, filters: NotebookFilters) -> NotebookPage:
    track_id, items = _filtered_items(session, filters)
    names = _names(track_id)
    entries = [_entry(item, names) for item in reversed(items)]  # newest first
    return NotebookPage(
        track_id=track_id,
        entries=entries,
        total=len(entries),
        counts_by_kind=dict(Counter(e.kind for e in entries)),
    )


def get_detail(session: Session, item_id: int) -> NotebookItemDetail:
    item = learning_item_repository.get_item(session, item_id)
    if item is None:
        raise ResourceNotFoundError(f"Notebook item {item_id} doesn't exist.")
    entry = _entry(item, _names(item.track_id))
    return NotebookItemDetail(
        **entry.model_dump(),
        content=item.content,
        reference_answer=item.reference_answer,
        rubric=item.rubric,
        history=[
            NotebookAttempt(
                created_at=a.created_at,
                score=a.score,
                answer_text=a.answer_text,
                selected_index=a.selected_index,
                grade=a.grade,
            )
            for a in item.attempts
        ],
        chat=[
            LessonChatMessage(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
            for m in item.chat_messages
        ],
    )


def export_pdf(session: Session, filters: NotebookFilters, notes_only: bool) -> tuple[bytes, str]:
    track_id, items = _filtered_items(session, filters)
    track = get_track(track_id)
    options = NotebookPdfOptions(
        track_name=track.name,
        date_from=filters.date_from,
        date_to=filters.date_to,
        notes_only=notes_only,
        generated_on=date.today(),
    )
    pdf = build_notebook_pdf(items, iter_subtopics_in_order(track_id), options)
    suffix = "revision-notes" if notes_only else "revision-book"
    return pdf, f"preppilot-{track_id.replace('_', '-')}-{suffix}-{date.today().isoformat()}.pdf"


def _names(track_id: str) -> dict[str, tuple[str, str]]:
    """subtopic id → (topic name, subtopic name)."""
    return {loc.subtopic.id: (loc.topic.name, loc.subtopic.name) for loc in iter_subtopics_in_order(track_id)}


def _entry(item: LearningItemRow, names: dict[str, tuple[str, str]]) -> NotebookEntry:
    topic_name, subtopic_name = names.get(item.subtopic_id, (item.topic_id, item.subtopic_id))
    return NotebookEntry(
        item_id=item.id,
        kind=item.kind,
        title=item.title,
        track_id=item.track_id,
        topic_id=item.topic_id,
        topic_name=topic_name,
        subtopic_id=item.subtopic_id,
        subtopic_name=subtopic_name,
        is_review=item.is_review,
        status=item.status,
        best_score=item.best_score,
        last_score=item.attempts[-1].score if item.attempts else None,
        attempts=len(item.attempts),
        key_points=item.key_points,
        has_chat=bool(item.chat_messages),
        created_at=item.created_at,
    )
