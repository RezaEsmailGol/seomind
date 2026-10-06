from fastapi.testclient import TestClient

from seomind.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_setup_status() -> None:
    response = client.get("/api/setup/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["steps"]["runtime"] is True
    assert payload["next"] == "google_oauth"
