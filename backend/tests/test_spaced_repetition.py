from datetime import date, timedelta

from app.learning.item_status import LearningStatus, status_after_score
from app.learning.spaced_repetition import ReviewState, quality_from_score, schedule_after_review

DAY = date(2026, 10, 1)


def test_good_answers_space_out_1_3_then_about_7_days() -> None:
    state = schedule_after_review(ReviewState(), 100, DAY)
    assert state.interval_days == 1 and state.due_on == DAY + timedelta(days=1)
    state = schedule_after_review(state, 100, DAY + timedelta(days=1))
    assert state.interval_days == 3
    state = schedule_after_review(state, 100, DAY + timedelta(days=4))
    assert state.interval_days >= 7


def test_low_score_resets_to_tomorrow_and_lowers_easiness() -> None:
    state = ReviewState(easiness=2.5, interval_days=8, repetitions=3, due_on=DAY)
    after = schedule_after_review(state, 30, DAY)
    assert after.repetitions == 0 and after.interval_days == 1
    assert after.easiness < 2.5


def test_same_day_good_answer_does_not_push_review_further_out() -> None:
    first = schedule_after_review(ReviewState(), 100, DAY)
    second = schedule_after_review(first, 100, DAY)
    assert second.due_on == first.due_on and second.repetitions == first.repetitions


def test_same_day_bad_answer_still_pulls_review_back() -> None:
    state = schedule_after_review(ReviewState(repetitions=3, interval_days=7, easiness=2.5), 100, DAY)
    worse = schedule_after_review(state, 20, DAY)
    assert worse.interval_days == 1


def test_quality_and_status_thresholds() -> None:
    assert [quality_from_score(s) for s in (0, 39, 60, 100)] == [0, 2, 3, 5]
    assert status_after_score(50) == LearningStatus.WEAK
    assert status_after_score(95) == LearningStatus.LEARNT  # first time: learnt, not yet mastered
    assert status_after_score(95, LearningStatus.LEARNT) == LearningStatus.MASTERED
