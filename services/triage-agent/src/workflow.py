from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from langgraph.graph import END, START, StateGraph

from .models import IncidentCreated, IncidentTriaged, TriageState

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama.platform.svc.cluster.local:11434")
OLLAMA_MODEL = "llama3"
VALID_SEVERITIES = {"low", "medium", "high", "critical"}

logger = logging.getLogger(__name__)


async def _ollama_generate(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return str(resp.json()["response"]).strip()


async def classify_severity(state: TriageState) -> dict[str, Any]:
    prompt = (
        "You are an incident triage assistant. "
        "Classify the severity of this incident.\n"
        "Respond with exactly one word: low, medium, high, or critical.\n\n"
        f"Title: {state['title']}\n"
        f"Description: {state['description']}"
    )
    raw = await _ollama_generate(prompt)
    severity = raw.lower().split()[0] if raw else "medium"
    if severity not in VALID_SEVERITIES:
        severity = "medium"
    logger.info(
        "classified severity",
        extra={"incident_id": state["id"], "severity": severity},
    )
    return {"severity": severity}


async def detect_duplicate(state: TriageState) -> dict[str, Any]:
    return {"is_duplicate": False, "duplicate_of": None}


async def assign_team(state: TriageState) -> dict[str, Any]:
    prompt = (
        "You are an incident routing assistant. "
        "Based on the severity and description below, "
        "assign a team name "
        "(one word: platform, backend, infra, frontend, data, security).\n"
        "Respond with exactly one word.\n\n"
        f"Severity: {state['severity']}\n"
        f"Description: {state['description']}"
    )
    raw = await _ollama_generate(prompt)
    team = raw.lower().split()[0] if raw else "platform"
    logger.info("assigned team", extra={"incident_id": state["id"], "team": team})
    return {"assigned_team": team}


def make_publish_node(js: Any) -> Any:
    async def publish_result(state: TriageState) -> dict[str, Any]:
        triaged = IncidentTriaged(
            id=state["id"],
            title=state["title"],
            description=state["description"],
            severity=state["severity"],
            source=state["source"],
            assigned_team=state["assigned_team"],
            is_duplicate=state["is_duplicate"],
            duplicate_of=state["duplicate_of"],
        )
        payload = triaged.model_dump_json().encode()
        await js.publish("incident.triaged", payload)
        logger.info("published triaged incident", extra={"incident_id": state["id"]})
        return {}

    return publish_result


def build_graph(js: Any) -> Any:
    graph: StateGraph[TriageState] = StateGraph(TriageState)
    graph.add_node("classify_severity", classify_severity)
    graph.add_node("detect_duplicate", detect_duplicate)
    graph.add_node("assign_team", assign_team)
    graph.add_node("publish_result", make_publish_node(js))
    graph.add_edge(START, "classify_severity")
    graph.add_edge("classify_severity", "detect_duplicate")
    graph.add_edge("detect_duplicate", "assign_team")
    graph.add_edge("assign_team", "publish_result")
    graph.add_edge("publish_result", END)
    return graph.compile()


async def run_triage_workflow(compiled_graph: Any, incident: IncidentCreated) -> None:
    initial_state: TriageState = {
        "id": incident.id,
        "title": incident.title,
        "description": incident.description,
        "source": incident.source,
        "created_at": incident.created_at.isoformat(),
        "severity": "unknown",
        "is_duplicate": False,
        "duplicate_of": None,
        "assigned_team": "",
    }
    await compiled_graph.ainvoke(initial_state)
