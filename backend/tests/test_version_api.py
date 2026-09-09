"""Tests for the GET /api/version endpoint."""

from fastapi.testclient import TestClient

from app.core.version import get_version


def test_get_version_endpoint(client: TestClient) -> None:
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["version"] == get_version()
