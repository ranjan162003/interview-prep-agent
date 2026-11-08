"""Today's plan: timed blocks, marking them done, and the end-of-day recap."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.plan_schemas import DailyPlan, DailyRecap
from app.services import planner_service

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/today", response_model=DailyPlan)
def read_today_plan(session: Session = Depends(get_db_session)) -> DailyPlan:
    return planner_service.get_today_plan(session)


@router.post("/today/regenerate", response_model=DailyPlan)
def regenerate_today_plan(session: Session = Depends(get_db_session)) -> DailyPlan:
    return planner_service.regenerate_today_plan(session)


@router.post("/today/blocks/{block_id}/complete", response_model=DailyPlan)
def complete_block(block_id: str, session: Session = Depends(get_db_session)) -> DailyPlan:
    return planner_service.complete_block(session, block_id)


@router.get("/today/recap", response_model=DailyRecap)
def read_today_recap(session: Session = Depends(get_db_session)) -> DailyRecap:
    return planner_service.get_today_recap(session)
