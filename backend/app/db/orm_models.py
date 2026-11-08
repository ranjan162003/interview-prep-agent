"""ORM tables.

`learning_items` is the learning notebook: one row for every lesson, question,
problem or lab the learner has been shown, kept forever so nothing is taught
twice and everything can be exported for revision. `attempts` holds each answer
given to an item, with its grade.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database_session import OrmBase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserProfileRow(OrmBase):
    """Single-user app: the profile is always row id 1."""

    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[str] = mapped_column(String(64))
    interview_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=60)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class LearningItemRow(OrmBase):
    __tablename__ = "learning_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[str] = mapped_column(String(64), index=True)
    topic_id: Mapped[str] = mapped_column(String(64), index=True)
    subtopic_id: Mapped[str] = mapped_column(String(64), index=True)
    # LearningItemKind: concept | quiz_question | coding_problem | security_lab | mock_question
    kind: Mapped[str] = mapped_column(String(32), index=True)
    # Shown again on purpose (spaced repetition), not taught as new.
    is_review: Mapped[bool] = mapped_column(Boolean, default=False)
    difficulty: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    # Kind-specific body: lesson text, quiz options, etc.
    content: Mapped[dict] = mapped_column(JSON)
    # Grading rubric (key points to cover, common mistakes) — written once, reused on every attempt.
    rubric: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The revision note: 3–5 bullets shown in the notebook and the PDF.
    key_points: Mapped[list] = mapped_column(JSON, default=list)
    # No-repeat rule: exact match on the fingerprint, near-duplicates via the normalised text.
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    normalized_text: Mapped[str] = mapped_column(Text)
    # LearningStatus: new | learnt | weak | mastered
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    best_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    attempts: Mapped[list[AttemptRow]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="AttemptRow.created_at"
    )
    chat_messages: Mapped[list[LessonChatMessageRow]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="LessonChatMessageRow.id"
    )


class AttemptRow(OrmBase):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id", ondelete="CASCADE"), index=True)
    answer_text: Mapped[str] = mapped_column(Text, default="")
    selected_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float] = mapped_column(Float)  # 0–100
    # Full grader output for explain-back answers (criteria, evidence, improved answer).
    grade: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)

    item: Mapped[LearningItemRow] = relationship(back_populates="attempts")


class LessonChatMessageRow(OrmBase):
    """One message in the "Ask the teacher" chat beside a lesson — kept for the notebook."""

    __tablename__ = "lesson_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    item: Mapped[LearningItemRow] = relationship(back_populates="chat_messages")


class ReviewScheduleRow(OrmBase):
    """SM-2 state per subtopic: when it next comes back for review."""

    __tablename__ = "review_schedule"
    __table_args__ = (UniqueConstraint("track_id", "subtopic_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[str] = mapped_column(String(64), index=True)
    subtopic_id: Mapped[str] = mapped_column(String(64))
    easiness: Mapped[float] = mapped_column(Float)
    interval_days: Mapped[int] = mapped_column(Integer)
    repetitions: Mapped[int] = mapped_column(Integer)
    due_on: Mapped[date] = mapped_column(Date, index=True)
    last_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_reviewed_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class DailyPlanRow(OrmBase):
    """The session built for one day. Blocks are JSON: kind, subtopic, minutes, reason, done."""

    __tablename__ = "daily_plans"
    __table_args__ = (UniqueConstraint("track_id", "plan_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[str] = mapped_column(String(64))
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    daily_minutes: Mapped[int] = mapped_column(Integer)
    blocks: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class MockSessionRow(OrmBase):
    __tablename__ = "mock_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[str] = mapped_column(String(64), index=True)
    # MockKind: technical | behavioural | mixed
    kind: Mapped[str] = mapped_column(String(16))
    # Learning item ids of the main questions, in order.
    question_item_ids: Mapped[list] = mapped_column(JSON)
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    # Follow-ups asked on the current main question.
    follow_ups_asked: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="in_progress")  # in_progress | finished
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)

    turns: Mapped[list[MockTurnRow]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="MockTurnRow.id"
    )


class MockTurnRow(OrmBase):
    __tablename__ = "mock_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("mock_sessions.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))  # interviewer | candidate
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    session: Mapped[MockSessionRow] = relationship(back_populates="turns")


class CoachConversationRow(OrmBase):
    __tablename__ = "coach_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, index=True)

    messages: Mapped[list[CoachMessageRow]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="CoachMessageRow.id"
    )


class CoachMessageRow(OrmBase):
    __tablename__ = "coach_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("coach_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    # Tools the coach used to answer (shown as "Looked at: your scores, …").
    tools_used: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    conversation: Mapped[CoachConversationRow] = relationship(back_populates="messages")
