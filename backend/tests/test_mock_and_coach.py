"""Mock interview (follow-ups, grading, finishing) and the coach's tool loop."""
from __future__ import annotations

import pytest

from tests.test_practice_api import OLLAMA, grade

QUESTIONS = {
    "questions": [
        {"question": "Tell me about a time you disagreed with a teammate.", "subtopic_id": "teamwork-conflict",
         "key_points": ["situation", "action", "result"], "reference_answer": "A strong STAR answer about a disagreement that ended well."},
        {"question": "Describe the hardest bug you have fixed and how you found it.", "subtopic_id": "projects-impact",
         "key_points": ["debugging steps", "result"], "reference_answer": "A strong STAR answer about a tricky production bug fix."},
    ]
}


@pytest.fixture
def swe(client):
    client.put("/api/profile", json={"track_id": "software_engineer"})


def follow_up(question: str) -> dict:
    return {"action": "follow_up", "follow_up_question": question, "acknowledgement": "Okay."}


MOVE_ON = {"action": "move_on", "follow_up_question": "", "acknowledgement": "Got it, thanks."}


def test_mock_interview_with_follow_ups_grades_each_question(client, provider, swe) -> None:
    provider.queue(QUESTIONS)
    mock = client.post("/api/mock/sessions", json={**OLLAMA, "kind": "behavioural", "question_count": 2}).json()
    assert mock["status"] == "in_progress" and mock["question_count"] == 2
    assert mock["turns"] == [{**mock["turns"][0], "role": "interviewer", "content": QUESTIONS["questions"][0]["question"]}]
    answer_url = f"/api/mock/sessions/{mock['id']}/answer"

    # Q1: a follow-up, then the interviewer moves on and the whole exchange is graded.
    provider.queue(follow_up("What was the result?"))
    mock = client.post(answer_url, json={**OLLAMA, "answer": "We disagreed about the database."}).json()
    assert mock["turns"][-1]["content"] == "Okay. What was the result?"
    provider.queue(MOVE_ON, grade((4, 3, 4, 3)))
    mock = client.post(answer_url, json={**OLLAMA, "answer": "We shipped on time."}).json()
    assert mock["grades"][0]["score"] == 70.0
    assert mock["turns"][-1]["content"].startswith("Got it, thanks. Next question: Describe the hardest bug")
    assert "Candidate: We disagreed about the database." in provider.prompts[-1]  # grader saw the full exchange
    assert "STAR" in provider.prompts[-1]  # behavioural → structure is graded as STAR

    # Q2: two follow-ups max, then it's graded without asking the interviewer again.
    provider.queue(follow_up("How did you find it?"), follow_up("What would you do differently?"))
    client.post(answer_url, json={**OLLAMA, "answer": "A race condition."})
    client.post(answer_url, json={**OLLAMA, "answer": "Logging."})
    provider.queue(grade((2, 2, 2, 2)))
    mock = client.post(answer_url, json={**OLLAMA, "answer": "Add tests."}).json()
    assert mock["status"] == "finished"
    assert [g["score"] for g in mock["grades"]] == [70.0, 40.0]
    assert mock["overall_score"] == 55.0

    assert client.post(answer_url, json={**OLLAMA, "answer": "more"}).status_code == 400
    sessions = client.get("/api/mock/sessions").json()
    assert sessions[0]["id"] == mock["id"] and sessions[0]["overall_score"] == 55.0
    # Mock questions land in the notebook too.
    assert client.get("/api/notebook", params={"kind": "mock_question"}).json()["total"] == 2


def test_ending_early_grades_only_the_answered_question(client, provider, swe) -> None:
    provider.queue(QUESTIONS)
    mock = client.post("/api/mock/sessions", json={**OLLAMA, "kind": "behavioural", "question_count": 2}).json()
    provider.queue(follow_up("And then?"))
    client.post(f"/api/mock/sessions/{mock['id']}/answer", json={**OLLAMA, "answer": "Something happened."})
    provider.queue(grade((3, 3, 3, 3)))
    ended = client.post(f"/api/mock/sessions/{mock['id']}/end", json=OLLAMA).json()
    assert ended["status"] == "finished" and len(ended["grades"]) == 1


def test_repeated_mock_questions_are_not_asked_again(client, provider, swe) -> None:
    provider.queue(QUESTIONS)
    client.post("/api/mock/sessions", json={**OLLAMA, "kind": "behavioural", "question_count": 2})
    fresh = {"question": "Tell me about yourself and why you want this role.", "subtopic_id": "tell-me-about-yourself",
             "key_points": ["present", "past", "future"], "reference_answer": "A strong present-past-future answer for this role."}
    provider.queue({"questions": [QUESTIONS["questions"][0], fresh]})
    mock = client.post("/api/mock/sessions", json={**OLLAMA, "kind": "behavioural", "question_count": 1}).json()
    assert mock["turns"][0]["content"] == fresh["question"]


def test_coach_uses_tools_then_answers_and_keeps_the_conversation(client, provider, swe) -> None:
    provider.queue(
        {"action": "tool", "tool": "get_progress", "arguments": {}},
        {"action": "tool", "tool": "no_such_tool", "arguments": {}},
        {"action": "answer", "answer": "Your readiness is **0%** — start with Big-O."},
    )
    reply = client.post("/api/coach/messages", json={**OLLAMA, "message": "How ready am I?"}).json()
    assert reply["messages"][1]["content"].startswith("Your readiness")
    assert reply["messages"][1]["tools_used"] == ["Checking your progress…", "no_such_tool"]
    last_prompt = provider.prompts[-1]
    assert '"readiness"' in last_prompt  # the tool result reached the model
    assert "ERROR: There is no tool called 'no_such_tool'" in last_prompt

    conversation_id = reply["conversation"]["id"]
    provider.queue("Plain text instead of JSON still works.")
    second = client.post("/api/coach/messages", json={**OLLAMA, "conversation_id": conversation_id, "message": "Thanks!"}).json()
    assert second["messages"][1]["content"] == "Plain text instead of JSON still works."
    assert "Learner: How ready am I?" in provider.prompts[-1]

    assert len(client.get(f"/api/coach/conversations/{conversation_id}").json()["messages"]) == 4
    assert client.get("/api/coach/conversations").json()[0]["title"] == "How ready am I?"
    assert client.delete(f"/api/coach/conversations/{conversation_id}").status_code == 204
    assert client.get("/api/coach/conversations").json() == []


def test_coach_must_answer_after_too_many_tool_calls(client, provider, swe) -> None:
    provider.queue(*[{"action": "tool", "tool": "get_weak_spots", "arguments": {}}] * 4,
                   {"action": "answer", "answer": "Done looking."})
    reply = client.post("/api/coach/messages", json={**OLLAMA, "message": "What am I weak at?"}).json()
    assert reply["messages"][1]["content"] == "Done looking."
    assert "used all your tool calls" in provider.prompts[-1]
