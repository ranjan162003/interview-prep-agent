"""Quiz and concept explain-back, end to end through the API with a scripted model."""
from __future__ import annotations

import pytest

OLLAMA = {"provider_id": "ollama"}


def quiz_question(text: str, correct: int = 0) -> dict:
    return {
        "question": text,
        "options": ["alpha", "beta", "gamma", "delta"],
        "correct_index": correct,
        "explanation": f"Because of {text}.",
        "key_point": f"Remember {text}.",
    }


def concept_lesson(title: str, prompt: str) -> dict:
    return {
        "title": title,
        "lesson_markdown": "A lesson body that is long enough to pass validation. " * 3,
        "explain_prompt": prompt,
        "key_points": ["Point one is stated.", "Point two is stated.", "Point three is stated."],
        "common_mistakes": ["Confusing it with something else."],
        "reference_answer": "A strong reference answer that is comfortably longer than forty characters.",
    }


DISTINCT_QUESTIONS = [
    "What does Big-O notation describe about an algorithm?",
    "Why is quicksort's worst case quadratic on sorted input?",
    "How much extra memory does a recursive DFS use on a skewed tree?",
]


def grade(scores: tuple[int, int, int, int]) -> dict:
    names = ["correctness", "depth", "clarity", "structure"]
    return {
        "criteria": [{"name": n, "score": s, "comment": "ok"} for n, s in zip(names, scores)],
        "covered_points": ["Point one is stated."],
        "missed_points": ["Point two is stated."],
        "evidence": [{"quote": "my words", "comment": "fine"}],
        "improved_answer": "A better answer.",
        "overall_feedback": "Good start.",
    }


@pytest.fixture
def profile(client):
    client.put("/api/profile", json={"track_id": "software_engineer"})


def test_practice_needs_a_profile_first(client, provider) -> None:
    response = client.post("/api/practice/quiz", json=OLLAMA)
    assert response.status_code == 400
    assert "Settings" in response.json()["detail"]


def test_quiz_hides_answers_and_grades_first_answer_only(client, provider, profile) -> None:
    provider.queue({"questions": [quiz_question(text, correct=1) for text in DISTINCT_QUESTIONS]})
    quiz = client.post("/api/practice/quiz", json={**OLLAMA, "question_count": 3}).json()

    assert quiz["subtopic"]["subtopic_id"] == "complexity-analysis"  # first subtopic in the syllabus
    assert len(quiz["questions"]) == 3
    assert "correct_index" not in quiz["questions"][0]

    item_id = quiz["questions"][0]["item_id"]
    wrong = client.post(f"/api/practice/quiz/{item_id}/answer", json={"selected_index": 0}).json()
    assert wrong["correct"] is False and wrong["correct_index"] == 1 and wrong["status"] == "weak"

    # Changing the answer after the reveal doesn't change the result.
    again = client.post(f"/api/practice/quiz/{item_id}/answer", json={"selected_index": 1}).json()
    assert again["correct"] is False and again["selected_index"] == 0


def test_quiz_drops_repeated_questions_and_regenerates(client, provider, profile) -> None:
    first = [quiz_question(text) for text in DISTINCT_QUESTIONS]
    provider.queue({"questions": first})
    client.post("/api/practice/quiz", json={**OLLAMA, "question_count": 3})

    # Second quiz: the model repeats one old question (reworded slightly), so one more is requested.
    provider.queue(
        {"questions": [
            quiz_question("What does Big O notation describe about an algorithm"),
            quiz_question("A brand new question about amortised analysis"),
            quiz_question("Another new question about recursion stack space"),
        ]},
        {"questions": [quiz_question("A third new question about worst case inputs")]},
    )
    quiz = client.post("/api/practice/quiz", json={**OLLAMA, "question_count": 3}).json()

    assert quiz["duplicates_skipped"] == 1
    assert [q["question"] for q in quiz["questions"]] == [
        "A brand new question about amortised analysis",
        "Another new question about recursion stack space",
        "A third new question about worst case inputs",
    ]
    # The model is told what was already asked, including the repeat it just made.
    assert "What does Big O notation describe about an algorithm" in provider.prompts[-1]


def test_concepts_follow_the_syllabus_then_switch_to_review(client, provider, profile) -> None:
    key_concepts = client.get("/api/tracks/software_engineer").json()["topics"][0]["subtopics"][0]["key_concepts"]

    for i, concept in enumerate(key_concepts):
        provider.queue(concept_lesson(f"Lesson {i} on {concept}", f"Explain {concept} in your own words, part {i}"))
        lesson = client.post("/api/practice/concept", json={**OLLAMA, "subtopic_id": "complexity-analysis"}).json()
        assert lesson["focus_concept"] == concept
        assert lesson["is_review"] is False

    overview = client.get("/api/practice/overview").json()
    first = next(s for s in overview["subtopics"] if s["subtopic_id"] == "complexity-analysis")
    assert first["status"] == "covered"
    assert overview["next_subtopic_id"] == "arrays-strings"

    provider.queue(concept_lesson("Review: comparing cases", "How do best and worst case differ for quicksort?"))
    review = client.post("/api/practice/concept", json={**OLLAMA, "subtopic_id": "complexity-analysis"}).json()
    assert review["is_review"] is True
    assert "REVIEW" in provider.prompts[-1]


def test_repeated_lesson_is_regenerated(client, provider, profile) -> None:
    provider.queue(concept_lesson("Big-O basics", "What does Big-O notation describe?"))
    client.post("/api/practice/concept", json={**OLLAMA, "subtopic_id": "complexity-analysis"})

    provider.queue(
        concept_lesson("Big-O basics", "What does Big-O notation describe?"),  # repeat → rejected
        concept_lesson("Best, average and worst case", "Why do interviewers ask about the worst case?"),
    )
    lesson = client.post("/api/practice/concept", json={**OLLAMA, "subtopic_id": "complexity-analysis"}).json()
    assert lesson["title"] == "Best, average and worst case"


def test_explanation_is_graded_saved_and_reveals_the_revision_note(client, provider, profile) -> None:
    provider.queue(concept_lesson("Big-O basics", "What does Big-O notation describe?"))
    lesson = client.post("/api/practice/concept", json=OLLAMA).json()
    assert "key_points" not in lesson  # the rubric isn't shown before answering

    provider.queue(grade((2, 1, 3, 2)))
    weak = client.post(f"/api/practice/concept/{lesson['item_id']}/explain", json={**OLLAMA, "answer": "It is speed."}).json()
    assert weak["score"] == 40.0  # (2+1+3+2) / 20, computed by the backend
    assert weak["status"] == "weak"
    assert weak["key_points"][0] == "Point one is stated."
    # The learner's answer reaches the grader as data between markers.
    assert "<<<ANSWER\nIt is speed.\nANSWER>>>" in provider.prompts[-1]

    provider.queue(grade((5, 4, 4, 4)))
    better = client.post(
        f"/api/practice/concept/{lesson['item_id']}/explain", json={**OLLAMA, "answer": "A fuller answer."}
    ).json()
    assert better["score"] == 85.0 and better["status"] == "learnt"


def test_wrong_item_kind_is_rejected(client, provider, profile) -> None:
    provider.queue({"questions": [quiz_question(text) for text in DISTINCT_QUESTIONS]})
    item_id = client.post("/api/practice/quiz", json={**OLLAMA, "question_count": 3}).json()["questions"][0]["item_id"]
    response = client.post(f"/api/practice/concept/{item_id}/explain", json={**OLLAMA, "answer": "x"})
    assert response.status_code == 400


def test_teacher_chat_answers_doubts_with_lesson_context_and_saves_them(client, provider, profile) -> None:
    provider.queue(concept_lesson("Big-O basics", "What does Big-O notation describe?"))
    lesson = client.post("/api/practice/concept", json=OLLAMA).json()
    chat_url = f"/api/practice/concept/{lesson['item_id']}/chat"
    assert client.get(chat_url).json() == []

    provider.queue({"reply": "Think of it like the **queue at a shop**."})
    first = client.post(chat_url, json={**OLLAMA, "message": "Can you explain it more simply?"}).json()
    assert [m["role"] for m in first] == ["user", "assistant"]
    assert first[1]["content"] == "Think of it like the **queue at a shop**."
    prompt = provider.prompts[-1]
    assert "A lesson body that is long enough" in prompt  # the lesson is in context
    assert "has NOT answered" in prompt  # don't hand over the graded answer yet
    assert "<<<QUESTION\nCan you explain it more simply?\nQUESTION>>>" in prompt

    # After answering the explain-back, the teacher may discuss the answer, and remembers the conversation.
    provider.queue(grade((4, 4, 4, 4)), {"reply": "Your answer covered it well."})
    client.post(f"/api/practice/concept/{lesson['item_id']}/explain", json={**OLLAMA, "answer": "An answer."})
    client.post(chat_url, json={**OLLAMA, "message": "Was my answer complete?"})
    prompt = provider.prompts[-1]
    assert "already answered" in prompt
    assert "Learner: Can you explain it more simply?" in prompt
    assert "Teacher: Think of it like the **queue at a shop**." in prompt

    assert len(client.get(chat_url).json()) == 4


def test_failed_teacher_call_saves_nothing(client, provider, profile) -> None:
    provider.queue(concept_lesson("Big-O basics", "What does Big-O notation describe?"))
    lesson = client.post("/api/practice/concept", json=OLLAMA).json()
    chat_url = f"/api/practice/concept/{lesson['item_id']}/chat"

    provider.queue("not json", "still not json")
    assert client.post(chat_url, json={**OLLAMA, "message": "Why?"}).status_code == 502
    assert client.get(chat_url).json() == []


def test_lessons_are_written_for_beginners(client, provider, profile) -> None:
    provider.queue(concept_lesson("Big-O basics", "What does Big-O notation describe?"))
    client.post("/api/practice/concept", json=OLLAMA)
    prompt = provider.prompts[-1]
    assert "complete" in prompt and "beginner" in prompt
    assert "### The big idea" in prompt and "everyday analogy" in prompt
