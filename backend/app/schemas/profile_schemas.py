"""The learner's setup: which track, the interview date, and how long a daily session is."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.core.utc_time import UtcDatetime

DailyMinutes = Literal[60, 120]


class ProfileUpdate(BaseModel):
    track_id: str
    # None means "no date yet, keep practising".
    interview_date: date | None = None
    daily_minutes: DailyMinutes = 60


class Profile(ProfileUpdate):
    track_name: str
    days_until_interview: int | None
    updated_at: UtcDatetime
