from __future__ import annotations

import json
import unittest.mock as mock

from src.main import process_message


def _make_msg(data: dict[str, object]) -> mock.AsyncMock:
    msg = mock.AsyncMock()
    msg.data = json.dumps(data).encode()
    return msg


def _valid_payload() -> dict[str, object]:
    return {
        "id": "abc-123",
        "title": "Service outage",
        "description": "API returning 500s",
        "severity": "unknown",
        "source": "alertmanager",
        "created_at": "2024-01-01T00:00:00Z",
    }


class TestProcessMessage:
    async def test_acks_on_successful_workflow(self) -> None:
        compiled_graph = mock.AsyncMock()
        msg = _make_msg(_valid_payload())

        with mock.patch("src.main.run_triage_workflow", new_callable=mock.AsyncMock):
            await process_message(compiled_graph, msg)

        msg.ack.assert_awaited_once()
        msg.nak.assert_not_awaited()

    async def test_naks_on_workflow_exception(self) -> None:
        compiled_graph = mock.AsyncMock()
        msg = _make_msg(_valid_payload())

        with mock.patch(
            "src.main.run_triage_workflow",
            side_effect=RuntimeError("ollama unreachable"),
        ):
            await process_message(compiled_graph, msg)

        msg.nak.assert_awaited_once()
        msg.ack.assert_not_awaited()

    async def test_naks_on_invalid_json(self) -> None:
        compiled_graph = mock.AsyncMock()
        msg = mock.AsyncMock()
        msg.data = b"not-valid-json"

        await process_message(compiled_graph, msg)

        msg.nak.assert_awaited_once()
        msg.ack.assert_not_awaited()

    async def test_naks_on_missing_required_field(self) -> None:
        compiled_graph = mock.AsyncMock()
        incomplete = {"id": "abc-123", "title": "oops"}
        msg = _make_msg(incomplete)

        await process_message(compiled_graph, msg)

        msg.nak.assert_awaited_once()
        msg.ack.assert_not_awaited()
