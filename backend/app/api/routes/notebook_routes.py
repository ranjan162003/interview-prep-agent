"""The learning notebook: browse, search and download everything learnt."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.notebook_schemas import NotebookItemDetail, NotebookPage
from app.services import notebook_service
from app.services.notebook_service import NotebookFilters

router = APIRouter(prefix="/notebook", tags=["notebook"])


def notebook_filters(
    track_id: str | None = None,
    kind: str | None = None,
    status: str | None = None,
    topic_id: str | None = None,
    q: str | None = Query(default=None, max_length=200),
    date_from: date | None = None,
    date_to: date | None = None,
) -> NotebookFilters:
    return NotebookFilters(track_id, kind, status, topic_id, q, date_from, date_to)


@router.get("", response_model=NotebookPage)
def list_notebook(
    filters: NotebookFilters = Depends(notebook_filters), session: Session = Depends(get_db_session)
) -> NotebookPage:
    return notebook_service.list_entries(session, filters)


@router.get("/items/{item_id}", response_model=NotebookItemDetail)
def read_notebook_item(item_id: int, session: Session = Depends(get_db_session)) -> NotebookItemDetail:
    return notebook_service.get_detail(session, item_id)


@router.get("/export.pdf", response_class=Response)
def export_notebook_pdf(
    mode: Literal["full", "notes"] = "full",
    filters: NotebookFilters = Depends(notebook_filters),
    session: Session = Depends(get_db_session),
) -> Response:
    pdf, filename = notebook_service.export_pdf(session, filters, notes_only=mode == "notes")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
