from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestHealth:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_content_type_is_json(self, client: TestClient) -> None:
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


class TestCreateIncident:
    def test_create_incident_returns_201(self, client: TestClient) -> None:
        payload = {
            "title": "DB connection pool exhausted",
            "description": "Postgres pool hit max connections on prod",
            "severity": "high",
            "source": "alertmanager",
        }
        response = client.post("/incidents", json=payload)
        assert response.status_code == 201

    def test_create_incident_response_shape(self, client: TestClient) -> None:
        payload = {
            "title": "Latency spike",
            "description": "p99 > 2s on checkout service",
        }
        response = client.post("/incidents", json=payload)
        data = response.json()
        assert data["status"] == "created"
        assert "id" in data
        assert len(data["id"]) == 36  # UUID4 canonical form
        assert data["title"] == "Latency spike"
        assert data["severity"] == "unknown"  # default
        assert data["source"] == "api"  # default

    def test_create_incident_missing_required_fields_returns_422(
        self, client: TestClient
    ) -> None:
        response = client.post("/incidents", json={"title": "Missing description"})
        assert response.status_code == 422
