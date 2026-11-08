"""Coding problems and security labs, end to end with a scripted model."""
from __future__ import annotations

import pytest

OLLAMA = {"provider_id": "ollama"}


def coding_problem(title: str = "Two Sum") -> dict:
    return {
        "title": title,
        "statement_markdown": f"Given a list of numbers and a target, return the indices of two numbers adding up to target. ({title})",
        "function_name": "two_sum",
        "starter_code": "def two_sum(nums: list[int], target: int) -> list[int]:\n    \"\"\"Return the two indices.\"\"\"\n    pass",
        "tests": [
            {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
            {"args": [[3, 2, 4], 6], "expected": [1, 2]},
            {"args": [[3, 3], 6], "expected": [0, 1]},
            {"args": [[1, 5, 9], 14], "expected": [1, 2]},
        ],
        "hints": ["Think about what you've seen.", "A dict maps value to index.", "Look up target - x."],
        "reference_solution": "def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen:\n            return [seen[target - x], i]\n        seen[x] = i",
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "key_points": ["Trade space for time with a hash map.", "Check the complement before inserting."],
    }


def code_review() -> dict:
    return {
        "correctness": "Fails when the pair is at the end.",
        "time_complexity": "O(n^2)",
        "space_complexity": "O(1)",
        "complexity_comment": "Use a dict for O(n).",
        "edge_cases_missed": ["duplicates"],
        "style_comments": ["Name variables clearly."],
        "improved_code": "def two_sum(nums, target): ...",
        "overall_feedback": "Good start.",
    }


def security_lab(title: str = "Brute force on SSH") -> dict:
    return {
        "title": title,
        "scenario_markdown": "You are a SOC analyst. An alert fired for repeated SSH failures. Investigate the log.",
        "artifact_type": "log",
        "artifact": "Oct 8 10:00:01 web sshd[1]: Failed password for root from 203.0.113.9 port 4242 ssh2\n" * 5,
        "tasks": [
            {"question": "Which IP is attacking?", "expected_answer": "203.0.113.9", "key_points": ["203.0.113.9"]},
            {"question": "How would you stop it?", "expected_answer": "Block the IP, disable root login, fail2ban", "key_points": ["block", "fail2ban"]},
        ],
        "key_points": ["Many failures from one IP means brute force.", "Disable root SSH login.", "Use fail2ban."],
        "walkthrough_markdown": "Count failures per IP, spot the outlier, then block it and harden SSH configuration.",
    }


@pytest.fixture
def swe(client):
    client.put("/api/profile", json={"track_id": "software_engineer"})


def test_coding_problem_hints_cost_points_and_tests_decide_the_score(client, provider, swe) -> None:
    provider.queue(coding_problem())
    problem = client.post("/api/practice/coding", json={**OLLAMA, "subtopic_id": "hashing"}).json()
    assert problem["function_name"] == "two_sum" and len(problem["tests"]) == 4
    assert problem["hint_count"] == 3 and problem["hints_used"] == 0

    item = problem["item_id"]
    first = client.post(f"/api/practice/coding/{item}/hint").json()
    second = client.post(f"/api/practice/coding/{item}/hint").json()
    assert (first["level"], second["level"]) == (1, 2)
    assert second["hint"] == "A dict maps value to index."

    provider.queue(code_review())
    results = [{"passed": True}] * 3 + [{"passed": False, "args": [[1, 5, 9], 14], "expected": [1, 2], "got": None}]
    review = client.post(
        f"/api/practice/coding/{item}/submit", json={**OLLAMA, "code": "def two_sum(n, t): ...", "results": results}
    ).json()
    assert (review["passed"], review["total"], review["hints_used"]) == (3, 4, 2)
    assert review["score"] == 55.0  # 75% of tests - 2 hints × 10
    assert review["status"] == "weak"
    # The failing case reaches the reviewer, and the code is marked as data.
    assert "args=[[1, 5, 9], 14]" in provider.prompts[-1] and "<<<CODE" in provider.prompts[-1]


def test_repeated_coding_problem_is_regenerated(client, provider, swe) -> None:
    provider.queue(coding_problem("Two Sum"))
    client.post("/api/practice/coding", json={**OLLAMA, "subtopic_id": "hashing"})
    provider.queue(coding_problem("Two Sum"), coding_problem("Group Anagrams Together By Sorted Key"))
    problem = client.post("/api/practice/coding", json={**OLLAMA, "subtopic_id": "hashing"}).json()
    assert problem["title"] == "Group Anagrams Together By Sorted Key"


def test_problem_whose_code_does_not_define_the_function_is_rejected(client, provider, swe) -> None:
    broken = {**coding_problem(), "reference_solution": "def other(): pass"}
    provider.queue(broken, coding_problem())  # first reply fails validation, the repair succeeds
    assert client.post("/api/practice/coding", json=OLLAMA).status_code == 200
    assert "must define" in provider.prompts[-1]


def test_security_lab_is_graded_per_task(client, provider) -> None:
    client.put("/api/profile", json={"track_id": "cybersecurity"})
    provider.queue(security_lab())
    lab = client.post("/api/practice/lab", json={**OLLAMA, "subtopic_id": "log-analysis"}).json()
    assert [t["question"] for t in lab["tasks"]] == ["Which IP is attacking?", "How would you stop it?"]
    assert "expected_answer" not in lab["tasks"][0]  # answers stay hidden until submitting

    url = f"/api/practice/lab/{lab['item_id']}/submit"
    assert client.post(url, json={**OLLAMA, "answers": ["only one"]}).status_code == 400

    provider.queue({"tasks": [{"score": 5, "comment": "Right."}, {"score": 2, "comment": "Partly.", "missed": ["fail2ban"]}],
                    "overall_feedback": "Count events per IP."})
    result = client.post(url, json={**OLLAMA, "answers": ["203.0.113.9", "block it"]}).json()
    assert result["score"] == 70.0 and result["status"] == "learnt"
    assert result["tasks"][1]["expected_answer"].startswith("Block the IP")
    assert result["tasks"][1]["missed"] == ["fail2ban"]
    assert "<<<ANSWER 2\nblock it\nANSWER 2>>>" in provider.prompts[-1]
