from datetime import date, timedelta

from app.syllabus.syllabus_loader import iter_subtopics_in_order, load_all_tracks


def test_both_tracks_load_with_key_concepts_everywhere() -> None:
    tracks = load_all_tracks()
    assert {"software_engineer", "cybersecurity"} <= set(tracks)
    for track in tracks.values():
        for location in iter_subtopics_in_order(track.id):
            assert location.subtopic.key_concepts, f"{track.id}/{location.subtopic.id} has no key concepts"


def test_tracks_endpoint_lists_summaries(client) -> None:
    response = client.get("/api/tracks")
    assert response.status_code == 200
    software = next(t for t in response.json() if t["id"] == "software_engineer")
    assert software["has_coding_problems"] is True
    assert software["subtopic_count"] > 20


def test_unknown_track_is_404(client) -> None:
    assert client.get("/api/tracks/astronaut").status_code == 404


def test_profile_is_null_until_saved_then_round_trips(client) -> None:
    assert client.get("/api/profile").json() is None

    interview = date.today() + timedelta(days=30)
    saved = client.put(
        "/api/profile",
        json={"track_id": "software_engineer", "interview_date": interview.isoformat(), "daily_minutes": 120},
    )
    assert saved.status_code == 200
    body = client.get("/api/profile").json()
    assert body["track_name"] == "Software engineer"
    assert body["days_until_interview"] == 30
    assert body["daily_minutes"] == 120


def test_profile_rejects_past_dates_and_unknown_tracks(client) -> None:
    past = (date.today() - timedelta(days=1)).isoformat()
    assert client.put("/api/profile", json={"track_id": "software_engineer", "interview_date": past}).status_code == 400
    assert client.put("/api/profile", json={"track_id": "astronaut"}).status_code == 404
    assert client.put("/api/profile", json={"track_id": "cybersecurity", "daily_minutes": 45}).status_code == 422
