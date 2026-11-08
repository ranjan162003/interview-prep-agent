"""Coach chat payloads."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.utc_time import UtcDatetime
from app.schemas.practice_schemas import AgentChoice


class CoachMessageRequest(AgentChoice):
    # None starts a new conversation.
    conversation_id: int | None = None
    message: str = Field(min_length=1, max_length=4000)


class CoachMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    tools_used: list[str]
    created_at: UtcDatetime


class CoachConversationSummary(BaseModel):
    id: int
    title: str
    updated_at: UtcDatetime


class CoachConversation(CoachConversationSummary):
    messages: list[CoachMessage]


class CoachReply(BaseModel):
    conversation: CoachConversationSummary
    messages: list[CoachMessage]
