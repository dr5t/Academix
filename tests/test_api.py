from academic_api.main import app
from fastapi.testclient import TestClient


def test_health_endpoint() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_configuration_does_not_expose_credentials() -> None:
    response = TestClient(app).get("/api/v1/configuration")
    assert response.status_code == 200
    assert "api_key" not in response.text.lower()
