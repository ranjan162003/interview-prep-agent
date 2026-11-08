"""Career tracks and their syllabus: track → topics → subtopics."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Subtopic(BaseModel):
    id: str
    name: str
    difficulty: int = Field(ge=1, le=3)
    key_concepts: list[str] = []


class Topic(BaseModel):
    id: str
    name: str
    description: str
    subtopics: list[Subtopic]


class Track(BaseModel):
    id: str
    name: str
    # Order in the track picker (lowest first).
    position: int = 100
    description: str
    has_coding_problems: bool
    topics: list[Topic]


class TrackSummary(BaseModel):
    id: str
    name: str
    description: str
    has_coding_problems: bool
    topic_count: int
    subtopic_count: int


class SubtopicLocation(BaseModel):
    """A subtopic plus the topic it belongs to — what agents need to write a question."""

    track: TrackSummary
    topic: Topic
    subtopic: Subtopic
