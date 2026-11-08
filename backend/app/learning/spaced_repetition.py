"""SM-2 spaced repetition, per subtopic: decides when a subtopic comes back for review.

A score maps to a 0-5 "quality". Below 3 the subtopic is treated as forgotten and
comes back tomorrow; otherwise the gap grows 1 → 3 → ~7 days and then keeps
multiplying by the easiness factor, which drifts down for subtopics that keep
scoring low and up for easy ones.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta

DEFAULT_EASINESS = 2.5
MIN_EASINESS = 1.3
FIRST_INTERVAL_DAYS = 1
SECOND_INTERVAL_DAYS = 3
PASSING_QUALITY = 3


@dataclass(frozen=True)
class ReviewState:
    easiness: float = DEFAULT_EASINESS
    interval_days: int = 0
    repetitions: int = 0
    due_on: date | None = None
    last_quality: int | None = None
    last_reviewed_on: date | None = None


def quality_from_score(score: float) -> int:
    """0–100 score → SM-2 quality 0–5."""
    return max(0, min(5, round(score / 20)))


def schedule_after_review(state: ReviewState, score: float, today: date) -> ReviewState:
    quality = quality_from_score(score)

    # Several answers on the same day count as one review: a later good answer
    # doesn't push the date out again, but a later bad one still pulls it back.
    if state.last_reviewed_on == today and quality >= PASSING_QUALITY:
        return replace(state, last_quality=min(quality, state.last_quality or quality))

    if quality < PASSING_QUALITY:
        repetitions, interval = 0, FIRST_INTERVAL_DAYS
    else:
        repetitions = state.repetitions + 1
        if repetitions == 1:
            interval = FIRST_INTERVAL_DAYS
        elif repetitions == 2:
            interval = SECOND_INTERVAL_DAYS
        else:
            interval = max(SECOND_INTERVAL_DAYS + 1, round(state.interval_days * state.easiness))

    easiness = state.easiness + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    return ReviewState(
        easiness=round(max(MIN_EASINESS, easiness), 3),
        interval_days=interval,
        repetitions=repetitions,
        due_on=today + timedelta(days=interval),
        last_quality=quality,
        last_reviewed_on=today,
    )
