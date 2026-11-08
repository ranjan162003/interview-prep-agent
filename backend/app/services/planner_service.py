"""Planner: builds today's session from the syllabus, the learner's coverage, reviews that are
due, and the session length.

The plan's *structure* is rule-based, not LLM-generated: it has to be reliable and
instant every morning. The agents fill each block with fresh content when it starts.
A missed day doesn't pile up — each plan only takes the most overdue reviews.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.app_exceptions import InvalidRequestError, ResourceNotFoundError
from app.db.orm_models import DailyPlanRow
from app.db.repositories import learning_item_repository
from app.learning.item_status import LearningStatus
from app.schemas.plan_schemas import DailyPlan, DailyRecap, PlanBlock, RecapItem
from app.schemas.practice_schemas import PracticeOverview
from app.schemas.track_schemas import SubtopicLocation
from app.services import practice_service, review_service
from app.services.profile_service import require_profile
from app.syllabus.syllabus_loader import get_track, iter_subtopics_in_order

# Topics where a hands-on security lab (logs, vulnerable code, HTTP requests) makes sense.
LAB_TOPIC_IDS = {
    "sec-networking", "os-security", "owasp", "vuln-pentest", "threats", "linux-logs",
    "incident-response", "cloud-security",
}
CODING_TOPIC_IDS = {"dsa"}


def get_today_plan(session: Session, today: date | None = None) -> DailyPlan:
    today = today or date.today()
    profile = require_profile(session)
    row = _get_row(session, profile.track_id, today)
    if row is None:
        row = DailyPlanRow(
            track_id=profile.track_id,
            plan_date=today,
            daily_minutes=profile.daily_minutes,
            blocks=[block.model_dump() for block in build_blocks(session, profile.track_id, profile.daily_minutes, today)],
        )
        session.add(row)
        session.commit()
    elif row.daily_minutes != profile.daily_minutes and not any(b["done"] for b in row.blocks):
        # Session length changed in Settings before starting: rebuild to fit.
        _rebuild(session, row, profile.daily_minutes, today)
    return _to_schema(row, profile.days_until_interview)


def regenerate_today_plan(session: Session, today: date | None = None) -> DailyPlan:
    today = today or date.today()
    profile = require_profile(session)
    row = _get_row(session, profile.track_id, today)
    if row is not None and any(b["done"] for b in row.blocks):
        raise InvalidRequestError("You've already finished part of today's plan, so it can't be rebuilt.")
    if row is None:
        return get_today_plan(session, today)
    _rebuild(session, row, profile.daily_minutes, today)
    return _to_schema(row, profile.days_until_interview)


def complete_block(session: Session, block_id: str, today: date | None = None) -> DailyPlan:
    today = today or date.today()
    profile = require_profile(session)
    row = _get_row(session, profile.track_id, today)
    if row is None or not any(b["id"] == block_id for b in row.blocks):
        raise ResourceNotFoundError(f"Today's plan has no block '{block_id}'.")
    # Reassign the list so SQLAlchemy notices the JSON change.
    row.blocks = [{**b, "done": True} if b["id"] == block_id else b for b in row.blocks]
    session.commit()
    return _to_schema(row, profile.days_until_interview)


def _rebuild(session: Session, row: DailyPlanRow, minutes: int, today: date) -> None:
    row.daily_minutes = minutes
    row.blocks = [block.model_dump() for block in build_blocks(session, row.track_id, minutes, today)]
    session.commit()


def _get_row(session: Session, track_id: str, day: date) -> DailyPlanRow | None:
    query = select(DailyPlanRow).where(DailyPlanRow.track_id == track_id, DailyPlanRow.plan_date == day)
    return session.scalars(query).first()


def _to_schema(row: DailyPlanRow, days_until_interview: int | None) -> DailyPlan:
    blocks = [PlanBlock.model_validate(b) for b in row.blocks]
    return DailyPlan(
        plan_date=row.plan_date,
        track_id=row.track_id,
        daily_minutes=row.daily_minutes,
        blocks=blocks,
        minutes_done=sum(b.minutes for b in blocks if b.done),
        days_until_interview=days_until_interview,
    )


# ---------- building the blocks ----------


def build_blocks(session: Session, track_id: str, daily_minutes: int, today: date) -> list[PlanBlock]:
    track = get_track(track_id)
    locations = {loc.subtopic.id: loc for loc in iter_subtopics_in_order(track_id)}
    overview = practice_service.get_overview(session)
    due = review_service.due_reviews(session, track_id, today)
    long_session = daily_minutes >= 120

    blocks: list[PlanBlock] = [_quiz_block(locations, overview, due, today, long_session)]
    blocks.append(_concept_block(locations, overview, "Concept of the day", 15))
    if long_session:
        weak = [s for s in overview.subtopics if s.status == "weak"]
        if weak:
            loc = locations[weak[0].subtopic_id]
            blocks.append(_block("concept", "Fix a weak spot", 15, loc, "You scored low here — a fresh explanation from a new angle.", True))
        else:
            blocks.append(_concept_block(locations, overview, "Second concept", 15))
    if track.has_coding_problems:
        blocks.append(_task_block("coding", "Coding problem", 45 if long_session else 25, locations, overview, CODING_TOPIC_IDS))
    else:
        blocks.append(_task_block("lab", "Security lab", 45 if long_session else 25, locations, overview, LAB_TOPIC_IDS))
    blocks.append(_mock_block(locations, overview, today, 25 if long_session else 10))
    blocks.append(PlanBlock(id="", kind="recap", title="Recap", minutes=5, reason="What you learnt today and what's next."))

    for index, block in enumerate(blocks, start=1):
        block.id = f"b{index}"
    # Block lengths are chosen so a plan fills the session exactly (checked in tests).
    return blocks


def _block(kind, title, minutes, loc: SubtopicLocation, reason: str, is_review: bool = False, **extra) -> PlanBlock:
    return PlanBlock(
        id="",
        kind=kind,
        title=title,
        minutes=minutes,
        subtopic_id=loc.subtopic.id,
        subtopic_name=loc.subtopic.name,
        topic_name=loc.topic.name,
        reason=reason,
        is_review=is_review,
        **extra,
    )


def _next_location(locations: dict[str, SubtopicLocation], overview: PracticeOverview) -> SubtopicLocation:
    if overview.next_subtopic_id:
        return locations[overview.next_subtopic_id]
    return next(iter(locations.values()))


def _quiz_block(locations, overview: PracticeOverview, due, today: date, long_session: bool) -> PlanBlock:
    minutes = 15 if long_session else 5
    if due:
        review = due[0]
        loc = locations.get(review.subtopic_id)
        if loc is not None:
            overdue = (today - review.due_on).days
            when = "today" if overdue <= 0 else f"{overdue} day{'s' if overdue != 1 else ''} ago"
            reason = f"Due for review ({when}) — spaced repetition keeps it from fading."
            if len(due) > 1:
                reason += f" {len(due) - 1} more subtopic(s) are waiting."
            return _block("quiz", "Warm-up quiz (review)", minutes, loc, reason, True)
    loc = _next_location(locations, overview)
    return _block("quiz", "Warm-up quiz", minutes, loc, "Warm up on the subtopic you're learning now.")


def _concept_block(locations, overview: PracticeOverview, title: str, minutes: int) -> PlanBlock:
    loc = _next_location(locations, overview)
    coverage = next((s for s in overview.subtopics if s.subtopic_id == loc.subtopic.id), None)
    taught = coverage.concepts_taught if coverage else 0
    reason = f"Next in your syllabus — concept {min(taught + 1, len(loc.subtopic.key_concepts))} of {len(loc.subtopic.key_concepts)}."
    return _block("concept", title, minutes, loc, reason)


def _task_block(kind, title, minutes, locations, overview: PracticeOverview, topic_ids: set[str]) -> PlanBlock:
    statuses = {s.subtopic_id: s.status for s in overview.subtopics}
    candidates = [loc for loc in locations.values() if loc.topic.id in topic_ids]
    if not candidates:
        candidates = list(locations.values())
    loc = next((c for c in candidates if statuses.get(c.subtopic.id) != "covered"), candidates[0])
    what = "problem" if kind == "coding" else "hands-on lab"
    return _block(kind, title, minutes, loc, f"A {what} on {loc.subtopic.name}, at your current level.")


def _mock_block(locations, overview: PracticeOverview, today: date, minutes: int) -> PlanBlock:
    practised = [s for s in overview.subtopics if s.status != "not_started"]
    behavioural_day = today.toordinal() % 3 == 0 or not practised
    if behavioural_day:
        return PlanBlock(
            id="",
            kind="mock",
            title="Mock interview question",
            minutes=minutes,
            reason="A behavioural question — practise telling a clear STAR story.",
            mock_kind="behavioural",
        )
    pick = practised[today.toordinal() % len(practised)]
    loc = locations[pick.subtopic_id]
    return _block(
        "mock", "Mock interview question", minutes, loc,
        f"An interview-style question on {loc.subtopic.name}, which you've already studied.", mock_kind="technical",
    )


# ---------- recap ----------


def get_today_recap(session: Session, today: date | None = None) -> DailyRecap:
    today = today or date.today()
    profile = require_profile(session)
    # Attempts are stored as naive UTC; "today" is the learner's local day.
    start = datetime.combine(today, time.min).astimezone(timezone.utc).replace(tzinfo=None)
    end = start + timedelta(days=1)

    locations = {loc.subtopic.id: loc for loc in iter_subtopics_in_order(profile.track_id)}
    items = [
        item
        for item in learning_item_repository.list_items(session, profile.track_id)
        if any(start <= attempt.created_at < end for attempt in item.attempts)
    ]
    overview = practice_service.get_overview(session)
    weak = [locations[s.subtopic_id].subtopic.name for s in overview.subtopics if s.status == "weak"]
    plan = _get_row(session, profile.track_id, today)
    tomorrow = today + timedelta(days=1)

    return DailyRecap(
        plan_date=today,
        minutes_done=sum(b["minutes"] for b in plan.blocks if b["done"]) if plan else 0,
        items=[
            RecapItem(
                item_id=item.id,
                kind=item.kind,
                title=item.title,
                subtopic_name=locations[item.subtopic_id].subtopic.name if item.subtopic_id in locations else item.subtopic_id,
                score=item.attempts[-1].score if item.attempts else None,
                status=LearningStatus(item.status),
                key_points=item.key_points,
            )
            for item in items
        ],
        weak_subtopics=weak,
        next_up=locations[overview.next_subtopic_id].subtopic.name if overview.next_subtopic_id else None,
        reviews_due_tomorrow=len(review_service.due_reviews(session, profile.track_id, tomorrow)),
    )
