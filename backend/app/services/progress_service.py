"""Progress numbers: streak, minutes studied, topic mastery and interview readiness.

Readiness is deliberately strict: a subtopic only counts in full once every key concept
has been taught *and* the learner scores well on it. Covering half the syllabus at
80% gives ~40% readiness, not 80%.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.orm_models import DailyPlanRow, LearningItemRow
from app.db.repositories import learning_item_repository
from app.learning.item_status import LearningItemKind, LearningStatus
from app.schemas.progress_schemas import (
    ActivityDay,
    ProgressOut,
    Readiness,
    ReadinessLabel,
    SubtopicMastery,
    TopicMastery,
)
from app.services import practice_service, review_service
from app.services.profile_service import require_profile
from app.syllabus.syllabus_loader import get_track

ACTIVITY_DAYS = 84  # 12 weeks for the calendar
RECENT_ITEMS_FOR_MASTERY = 10
RECENT_ANSWERS_FOR_AVERAGE = 30

READINESS_LABELS: list[tuple[float, ReadinessLabel]] = [
    (80, "Interview ready"),
    (60, "Nearly ready"),
    (35, "Getting there"),
    (10, "Building foundations"),
    (0, "Getting started"),
]


def local_day(stored_utc: datetime) -> date:
    """Timestamps are stored as naive UTC; streaks and calendars use the learner's local day."""
    return stored_utc.replace(tzinfo=timezone.utc).astimezone().date()


def get_progress(session: Session, today: date | None = None) -> ProgressOut:
    today = today or date.today()
    profile = require_profile(session)
    track = get_track(profile.track_id)
    items = learning_item_repository.list_items(session, profile.track_id)
    overview = {c.subtopic_id: c for c in practice_service.get_overview(session).subtopics}
    schedule = {row.subtopic_id: row for row in review_service.list_schedule(session, profile.track_id)}

    by_subtopic: dict[str, list[LearningItemRow]] = defaultdict(list)
    for item in items:
        by_subtopic[item.subtopic_id].append(item)

    topics: list[TopicMastery] = []
    all_subtopics: list[SubtopicMastery] = []
    for topic in track.topics:
        subtopics = []
        for subtopic in topic.subtopics:
            coverage = overview[subtopic.id]
            entry = SubtopicMastery(
                subtopic_id=subtopic.id,
                name=subtopic.name,
                difficulty=subtopic.difficulty,
                mastery=subtopic_mastery(by_subtopic.get(subtopic.id, [])),
                coverage=min(1.0, coverage.concepts_taught / coverage.key_concept_count) if coverage.key_concept_count else 0.0,
                status=coverage.status,
                next_review_on=schedule[subtopic.id].due_on if subtopic.id in schedule else None,
            )
            subtopics.append(entry)
        all_subtopics.extend(subtopics)
        scored = [s.mastery for s in subtopics if s.mastery is not None]
        topics.append(
            TopicMastery(
                topic_id=topic.id,
                name=topic.name,
                mastery=round(sum(scored) / len(scored), 1) if scored else None,
                coverage=round(sum(s.coverage for s in subtopics) / len(subtopics), 3),
                subtopics=subtopics,
            )
        )

    attempts = [attempt for item in items for attempt in item.attempts]
    answers_per_day = Counter(local_day(a.created_at) for a in attempts)
    minutes_per_day = _minutes_per_day(session, profile.track_id)
    active_days = {day for day, count in answers_per_day.items() if count} | {d for d, m in minutes_per_day.items() if m}
    streak, longest = streaks(active_days, today)

    recent = sorted(attempts, key=lambda a: a.created_at)[-RECENT_ANSWERS_FOR_AVERAGE:]
    week_start = today - timedelta(days=6)

    return ProgressOut(
        track_id=track.id,
        track_name=track.name,
        days_until_interview=profile.days_until_interview,
        streak_days=streak,
        longest_streak=longest,
        minutes_total=sum(minutes_per_day.values()),
        minutes_this_week=sum(m for d, m in minutes_per_day.items() if week_start <= d <= today),
        items_seen=len(items),
        items_learnt=sum(1 for i in items if i.status in (LearningStatus.LEARNT, LearningStatus.MASTERED)),
        answers_total=len(attempts),
        average_recent_score=round(sum(a.score for a in recent) / len(recent), 1) if recent else None,
        reviews_due=len(review_service.due_reviews(session, profile.track_id, today)),
        readiness=readiness(all_subtopics, items),
        activity=[
            ActivityDay(day=day, answers=answers_per_day.get(day, 0), minutes=minutes_per_day.get(day, 0))
            for day in (today - timedelta(days=offset) for offset in range(ACTIVITY_DAYS - 1, -1, -1))
        ],
        topics=topics,
    )


def subtopic_mastery(items: list[LearningItemRow]) -> float | None:
    """Mean of the latest score on the most recent answered items (recent work counts most)."""
    answered = [item for item in items if item.attempts]
    if not answered:
        return None
    recent = sorted(answered, key=lambda item: item.attempts[-1].created_at)[-RECENT_ITEMS_FOR_MASTERY:]
    return round(sum(item.attempts[-1].score for item in recent) / len(recent), 1)


def readiness(subtopics: list[SubtopicMastery], items: list[LearningItemRow]) -> Readiness:
    coverage = sum(s.coverage for s in subtopics) / len(subtopics) * 100 if subtopics else 0.0
    scored = [s.mastery for s in subtopics if s.mastery is not None]
    mastery = sum(scored) / len(scored) if scored else None
    score = sum(s.coverage * (s.mastery or 0) for s in subtopics) / len(subtopics) if subtopics else 0.0

    mock_scores = [
        item.attempts[-1].score for item in items if item.kind == LearningItemKind.MOCK_QUESTION and item.attempts
    ]
    label = next(name for floor, name in READINESS_LABELS if score >= floor)
    return Readiness(
        score=round(score, 1),
        label=label,
        coverage_percent=round(coverage, 1),
        mastery_percent=round(mastery, 1) if mastery is not None else None,
        mock_average=round(sum(mock_scores) / len(mock_scores), 1) if mock_scores else None,
    )


def streaks(active_days: set[date], today: date) -> tuple[int, int]:
    """(current streak, longest streak). Today not studied yet doesn't break a streak that ran to yesterday."""
    current = 0
    day = today if today in active_days else today - timedelta(days=1)
    while day in active_days:
        current += 1
        day -= timedelta(days=1)

    longest = run = 0
    previous: date | None = None
    for day in sorted(active_days):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    return current, longest


def _minutes_per_day(session: Session, track_id: str) -> dict[date, int]:
    plans = session.scalars(select(DailyPlanRow).where(DailyPlanRow.track_id == track_id))
    return {plan.plan_date: sum(b["minutes"] for b in plan.blocks if b.get("done")) for plan in plans}
