"""Queries over the learning notebook (`learning_items` + `attempts`)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.orm_models import AttemptRow, LearningItemRow


def list_items(
    session: Session,
    track_id: str,
    subtopic_id: str | None = None,
    kind: str | None = None,
) -> list[LearningItemRow]:
    query = (
        select(LearningItemRow)
        .where(LearningItemRow.track_id == track_id)
        .options(selectinload(LearningItemRow.attempts), selectinload(LearningItemRow.chat_messages))
        .order_by(LearningItemRow.created_at, LearningItemRow.id)
    )
    if subtopic_id is not None:
        query = query.where(LearningItemRow.subtopic_id == subtopic_id)
    if kind is not None:
        query = query.where(LearningItemRow.kind == kind)
    return list(session.scalars(query))


def get_item(session: Session, item_id: int) -> LearningItemRow | None:
    return session.get(LearningItemRow, item_id, options=[selectinload(LearningItemRow.attempts)])


def add_items(session: Session, items: list[LearningItemRow]) -> list[LearningItemRow]:
    session.add_all(items)
    session.commit()
    return items


def add_attempt(session: Session, item: LearningItemRow, attempt: AttemptRow) -> AttemptRow:
    item.attempts.append(attempt)
    session.commit()
    return attempt
