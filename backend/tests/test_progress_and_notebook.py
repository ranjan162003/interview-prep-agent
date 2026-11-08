from datetime import date, timedelta

import pytest

from app.learning.notebook_pdf_builder import _count_label, clean, inline
from app.services.progress_service import streaks
from tests.test_practice_api import DISTINCT_QUESTIONS, OLLAMA, concept_lesson, grade, quiz_question
from tests.test_tasks_api import code_review, coding_problem

TODAY = date(2026, 10, 8)


@pytest.fixture
def studied(client, provider):
    """A learner who did a quiz, a graded lesson with a teacher chat, and a coding problem today."""
    client.put("/api/profile", json={"track_id": "software_engineer"})
    provider.queue({"questions": [quiz_question(text, correct=1) for text in DISTINCT_QUESTIONS]})
    quiz = client.post("/api/practice/quiz", json={**OLLAMA, "subtopic_id": "complexity-analysis", "question_count": 3}).json()
    client.post(f"/api/practice/quiz/{quiz['questions'][0]['item_id']}/answer", json={"selected_index": 1})
    client.post(f"/api/practice/quiz/{quiz['questions'][1]['item_id']}/answer", json={"selected_index": 0})

    provider.queue(concept_lesson("Big-O basics", "What does Big-O notation describe?"), grade((4, 4, 4, 4)))
    lesson = client.post("/api/practice/concept", json={**OLLAMA, "subtopic_id": "complexity-analysis"}).json()
    client.post(f"/api/practice/concept/{lesson['item_id']}/explain", json={**OLLAMA, "answer": "Growth rate → as n grows."})
    provider.queue({"reply": "Think of a **queue** ✓"})
    client.post(f"/api/practice/concept/{lesson['item_id']}/chat", json={**OLLAMA, "message": "Simpler please?"})

    provider.queue(coding_problem(), code_review())
    problem = client.post("/api/practice/coding", json={**OLLAMA, "subtopic_id": "hashing"}).json()
    client.post(
        f"/api/practice/coding/{problem['item_id']}/submit",
        json={**OLLAMA, "code": "def two_sum(nums, target):\n    return [0, 1]", "results": [{"passed": True}, {"passed": False}]},
    )
    return {"lesson": lesson["item_id"], "problem": problem["item_id"]}


def test_streaks_count_back_from_today_or_yesterday() -> None:
    days = {TODAY - timedelta(days=n) for n in (1, 2, 3, 7, 8)}
    assert streaks(days, TODAY) == (3, 3)  # not studied yet today: the streak still stands
    assert streaks(days | {TODAY}, TODAY) == (4, 4)
    assert streaks({TODAY - timedelta(days=2)}, TODAY) == (0, 1)


def test_progress_reflects_todays_work(client, studied) -> None:
    progress = client.get("/api/progress").json()
    assert progress["streak_days"] == 1
    assert progress["items_seen"] == 5 and progress["answers_total"] == 4
    assert len(progress["activity"]) == 84 and progress["activity"][-1]["answers"] == 4

    dsa = next(t for t in progress["topics"] if t["topic_id"] == "dsa")
    complexity = next(s for s in dsa["subtopics"] if s["subtopic_id"] == "complexity-analysis")
    assert complexity["coverage"] == 0.25  # 1 of 4 key concepts taught
    assert complexity["mastery"] is not None and complexity["next_review_on"] is not None
    assert 0 < progress["readiness"]["score"] < 10
    assert progress["readiness"]["label"] == "Getting started"


def test_notebook_lists_filters_and_shows_full_detail(client, studied) -> None:
    page = client.get("/api/notebook").json()
    assert page["total"] == 5
    assert page["counts_by_kind"] == {"quiz_question": 3, "concept": 1, "coding_problem": 1}
    assert page["entries"][0]["kind"] == "coding_problem"  # newest first

    assert client.get("/api/notebook", params={"kind": "concept"}).json()["total"] == 1
    assert client.get("/api/notebook", params={"q": "big-o"}).json()["total"] >= 1
    assert client.get("/api/notebook", params={"status": "weak"}).json()["total"] == 2

    detail = client.get(f"/api/notebook/items/{studied['lesson']}").json()
    assert detail["has_chat"] and [m["role"] for m in detail["chat"]] == ["user", "assistant"]
    assert detail["history"][0]["score"] == 80.0
    assert "lesson_markdown" in detail["content"]
    assert client.get("/api/notebook/items/99999").status_code == 404


def test_pdf_export_full_and_notes(client, studied) -> None:
    full = client.get("/api/notebook/export.pdf")
    assert full.status_code == 200
    assert full.headers["content-type"] == "application/pdf"
    assert "revision-book" in full.headers["content-disposition"]
    assert full.content.startswith(b"%PDF")

    notes = client.get("/api/notebook/export.pdf", params={"mode": "notes"})
    assert notes.content.startswith(b"%PDF") and len(notes.content) < len(full.content)

    future = (date.today() + timedelta(days=5)).isoformat()
    empty = client.get("/api/notebook/export.pdf", params={"date_from": future})
    assert empty.status_code == 200 and empty.content.startswith(b"%PDF")


def test_pdf_text_helpers_handle_symbols_and_markup() -> None:
    assert clean("a → b ≤ c ✓") == "a -> b <= c [yes]"
    assert inline("**bold** and `x < y` and *it*") == (
        '<b>bold</b> and <font name="Courier">x &lt; y</font> and <i>it</i>'
    )


def test_cover_counts_read_naturally() -> None:
    assert _count_label(3, "Quiz") == "3 quiz questions"
    assert _count_label(1, "Quiz") == "1 quiz question"
    assert _count_label(2, "Coding problem") == "2 coding problems"
    assert _count_label(1, "Concept") == "1 concept"
