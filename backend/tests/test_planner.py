from datetime import date, timedelta

from tests.test_practice_api import DISTINCT_QUESTIONS, OLLAMA, quiz_question


def test_first_day_plan_follows_the_syllabus(client) -> None:
    client.put("/api/profile", json={"track_id": "software_engineer", "daily_minutes": 60})
    plan = client.get("/api/plans/today").json()

    kinds = [b["kind"] for b in plan["blocks"]]
    assert kinds == ["quiz", "concept", "coding", "mock", "recap"]
    assert sum(b["minutes"] for b in plan["blocks"]) == 60
    assert plan["blocks"][1]["subtopic_id"] == "complexity-analysis"
    assert plan["blocks"][3]["mock_kind"] == "behavioural"  # nothing practised yet
    # The same plan comes back all day.
    assert client.get("/api/plans/today").json() == plan


def test_cyber_two_hour_plan_has_a_lab_and_two_concepts(client) -> None:
    client.put("/api/profile", json={"track_id": "cybersecurity", "daily_minutes": 120})
    blocks = client.get("/api/plans/today").json()["blocks"]
    assert [b["kind"] for b in blocks] == ["quiz", "concept", "concept", "lab", "mock", "recap"]
    assert sum(b["minutes"] for b in blocks) == 120


def test_completing_blocks_and_changing_session_length(client) -> None:
    client.put("/api/profile", json={"track_id": "software_engineer", "daily_minutes": 60})
    client.get("/api/plans/today")
    # Changing the length before starting rebuilds the plan…
    client.put("/api/profile", json={"track_id": "software_engineer", "daily_minutes": 120})
    assert client.get("/api/plans/today").json()["daily_minutes"] == 120

    done = client.post("/api/plans/today/blocks/b1/complete").json()
    assert done["blocks"][0]["done"] is True and done["minutes_done"] == 15
    # …but not once something is done.
    assert client.post("/api/plans/today/regenerate").status_code == 400
    assert client.post("/api/plans/today/blocks/nope/complete").status_code == 404


def test_a_failed_quiz_puts_the_subtopic_up_for_review_and_into_the_recap(client, provider) -> None:
    client.put("/api/profile", json={"track_id": "software_engineer"})
    provider.queue({"questions": [quiz_question(text, correct=1) for text in DISTINCT_QUESTIONS]})
    quiz = client.post("/api/practice/quiz", json={**OLLAMA, "subtopic_id": "hashing", "question_count": 3}).json()
    client.post(f"/api/practice/quiz/{quiz['questions'][0]['item_id']}/answer", json={"selected_index": 0})

    from app.services import planner_service, review_service
    from app.db.database_session import get_db_session

    session = next(client.app.dependency_overrides[get_db_session]())
    tomorrow = date.today() + timedelta(days=1)
    assert [r.subtopic_id for r in review_service.due_reviews(session, "software_engineer", tomorrow)] == ["hashing"]
    blocks = planner_service.build_blocks(session, "software_engineer", 60, tomorrow)
    assert blocks[0].subtopic_id == "hashing" and blocks[0].is_review

    recap = client.get("/api/plans/today/recap").json()
    assert [i["title"] for i in recap["items"]] == [DISTINCT_QUESTIONS[0]]
    assert recap["reviews_due_tomorrow"] == 1
    assert "Hash maps and sets" in recap["weak_subtopics"]
