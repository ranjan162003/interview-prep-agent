from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_provider_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.get("/api/providers/not-a-provider")
    assert response.status_code == 422


def test_ollama_cannot_store_an_api_key() -> None:
    with TestClient(app) as client:
        response = client.put("/api/providers/ollama/api-key", json={"api_key": "x" * 20})
    assert response.status_code == 400
    assert "doesn't use an API key" in response.json()["detail"]
