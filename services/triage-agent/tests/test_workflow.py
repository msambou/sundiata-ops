from __future__ import annotations

import json
import unittest.mock as mock

from src.models import TriageState
from src.workflow import (
    assign_team,
    classify_severity,
    detect_duplicate,
    make_publish_node,
)


def _base_state(**overrides: object) -> TriageState:
    base: TriageState = {
        "id": "test-uuid",
        "title": "DB down",
        "description": "Postgres connection refused on prod",
        "source": "alertmanager",
        "created_at": "2024-01-01T00:00:00Z",
        "severity": "unknown",
        "is_duplicate": False,
        "duplicate_of": None,
        "assigned_team": "",
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


def _make_ollama_mock(response_text: str) -> mock.AsyncMock:
    mock_response = mock.MagicMock()
    mock_response.json.return_value = {"response": response_text}
    mock_response.raise_for_status = mock.MagicMock()

    mock_client = mock.AsyncMock()
    mock_client.post = mock.AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mock.AsyncMock(return_value=None)
    return mock_client


class TestClassifySeverity:
    async def test_sets_severity_from_ollama_response(self) -> None:
        mock_client = _make_ollama_mock("high")
        with mock.patch("src.workflow.httpx.AsyncClient", return_value=mock_client):
            result = await classify_severity(_base_state())
        assert result == {"severity": "high"}

    async def test_handles_mixed_case_response(self) -> None:
        mock_client = _make_ollama_mock("Critical")
        with mock.patch("src.workflow.httpx.AsyncClient", return_value=mock_client):
            result = await classify_severity(_base_state())
        assert result == {"severity": "critical"}

    async def test_defaults_to_medium_for_unrecognized_response(self) -> None:
        mock_client = _make_ollama_mock("urgent")
        with mock.patch("src.workflow.httpx.AsyncClient", return_value=mock_client):
            result = await classify_severity(_base_state())
        assert result == {"severity": "medium"}

    async def test_defaults_to_medium_for_empty_response(self) -> None:
        mock_client = _make_ollama_mock("")
        with mock.patch("src.workflow.httpx.AsyncClient", return_value=mock_client):
            result = await classify_severity(_base_state())
        assert result == {"severity": "medium"}


class TestDetectDuplicate:
    async def test_always_returns_not_duplicate(self) -> None:
        result = await detect_duplicate(_base_state())
        assert result == {"is_duplicate": False, "duplicate_of": None}


class TestAssignTeam:
    async def test_sets_assigned_team_from_ollama_response(self) -> None:
        mock_client = _make_ollama_mock("platform")
        with mock.patch("src.workflow.httpx.AsyncClient", return_value=mock_client):
            result = await assign_team(_base_state(severity="high"))
        assert result == {"assigned_team": "platform"}

    async def test_lowercases_team_name(self) -> None:
        mock_client = _make_ollama_mock("Backend")
        with mock.patch("src.workflow.httpx.AsyncClient", return_value=mock_client):
            result = await assign_team(_base_state(severity="medium"))
        assert result == {"assigned_team": "backend"}

    async def test_defaults_to_platform_for_empty_response(self) -> None:
        mock_client = _make_ollama_mock("")
        with mock.patch("src.workflow.httpx.AsyncClient", return_value=mock_client):
            result = await assign_team(_base_state(severity="low"))
        assert result == {"assigned_team": "platform"}


class TestPublishResult:
    async def test_publishes_to_incident_triaged(self) -> None:
        mock_js = mock.AsyncMock()
        publish_node = make_publish_node(mock_js)
        state = _base_state(severity="high", assigned_team="platform")

        await publish_node(state)

        mock_js.publish.assert_awaited_once()
        subject, payload = mock_js.publish.call_args[0]
        assert subject == "incident.triaged"
        data = json.loads(payload)
        assert data["severity"] == "high"
        assert data["assigned_team"] == "platform"
        assert data["is_duplicate"] is False
        assert data["id"] == "test-uuid"

    async def test_returns_empty_dict(self) -> None:
        mock_js = mock.AsyncMock()
        publish_node = make_publish_node(mock_js)
        result = await publish_node(_base_state(severity="low", assigned_team="infra"))
        assert result == {}
