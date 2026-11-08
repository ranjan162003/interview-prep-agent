"""What kind of thing a learning item is, and how a score moves it between statuses."""
from __future__ import annotations

from enum import Enum

# A score at or above this means the idea is learnt; below it, the item is weak and comes back sooner.
LEARNT_SCORE_THRESHOLD = 70.0


class LearningItemKind(str, Enum):
    CONCEPT = "concept"
    QUIZ_QUESTION = "quiz_question"
    CODING_PROBLEM = "coding_problem"
    SECURITY_LAB = "security_lab"
    MOCK_QUESTION = "mock_question"


class LearningStatus(str, Enum):
    NEW = "new"
    LEARNT = "learnt"
    WEAK = "weak"
    MASTERED = "mastered"


# A second strong answer on something already learnt marks it mastered.
MASTERED_SCORE_THRESHOLD = 90.0


def status_after_score(score: float, previous: LearningStatus = LearningStatus.NEW) -> LearningStatus:
    if score < LEARNT_SCORE_THRESHOLD:
        return LearningStatus.WEAK
    if score >= MASTERED_SCORE_THRESHOLD and previous in (LearningStatus.LEARNT, LearningStatus.MASTERED):
        return LearningStatus.MASTERED
    return LearningStatus.LEARNT
