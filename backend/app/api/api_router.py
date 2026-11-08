"""Collects every route module under the `/api` prefix."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    coach_routes,
    health_routes,
    mock_routes,
    notebook_routes,
    plan_routes,
    practice_routes,
    profile_routes,
    progress_routes,
    provider_routes,
    track_routes,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(health_routes.router)
api_router.include_router(provider_routes.router)
api_router.include_router(track_routes.router)
api_router.include_router(profile_routes.router)
api_router.include_router(practice_routes.router)
api_router.include_router(plan_routes.router)
api_router.include_router(progress_routes.router)
api_router.include_router(notebook_routes.router)
api_router.include_router(mock_routes.router)
api_router.include_router(coach_routes.router)
