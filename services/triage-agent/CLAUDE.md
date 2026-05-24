# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See the root `CLAUDE.md` for project-wide conventions (Dockerfile pattern, pyproject.toml, Helm naming, OTel setup, NATS topics).

## Role

Classifies incoming incidents by severity, detects duplicates, and routes them to the appropriate downstream agents by publishing to `incident.triaged`.

## Source Layout

```
src/
├── main.py       # NATS subscriber loop, OTel setup, graceful shutdown
├── models.py     # Pydantic input/output models (IncidentCreated, IncidentTriaged)
└── workflow.py   # LangGraph StateGraph (classify_severity → detect_duplicate → assign_team → publish_result)
tests/
├── test_main.py      # NATS connection and message handling
└── test_workflow.py  # Individual graph node tests (mock httpx for Ollama calls)
```

## NATS

- **Subscribes to:** `incident.created`
- **Publishes to:** `incident.triaged`
- **Consumer group:** `triage-agent` (durable, queue group for horizontal scaling)

## Input / Output Models

**Input** (from `incident.created`):
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "severity": "unknown",
  "source": "string",
  "created_at": "ISO8601"
}
```

**Output** (to `incident.triaged`):
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "severity": "low | medium | high | critical",
  "source": "string",
  "assigned_team": "string",
  "is_duplicate": false,
  "duplicate_of": "uuid | null",
  "triaged_at": "ISO8601"
}
```

## LangGraph Workflow

StateGraph nodes in order:

1. **`classify_severity`** — Prompt Ollama with the incident title + description. Ask it to return one of: `low`, `medium`, `high`, `critical`. Parse the response and set `state.severity`.
2. **`detect_duplicate`** — Stub for now: always returns `is_duplicate: false`. Future: query a vector store or recent incident cache.
3. **`assign_team`** — Prompt Ollama with the classified severity and description. Ask it to suggest a team name (e.g. "platform", "backend", "infra"). Set `state.assigned_team`.
4. **`publish_result`** — Serialize the triaged incident and publish to `incident.triaged`.

Edges: `classify_severity` → `detect_duplicate` → `assign_team` → `publish_result`

## Ollama Usage

- **Model:** `llama3`
- **Endpoint:** `http://ollama.platform.svc.cluster.local:11434`
- **Client:** use `httpx.AsyncClient` to POST to `/api/generate`
- Keep prompts short and instruct the model to respond with a single word or JSON only — do not ask for explanations

Example severity prompt:
```
You are an incident triage assistant. Classify the severity of this incident.
Respond with exactly one word: low, medium, high, or critical.

Title: {title}
Description: {description}
```

## Key Dependencies

Beyond the common set in root `CLAUDE.md`:
- `langgraph>=0.4.0` — StateGraph orchestration
- `nats-py>=2.9.0` — NATS JetStream client
- `httpx>=0.28.0` — async HTTP client for Ollama

## No HTTP Endpoints

This service is event-driven only. It has no FastAPI app and no HTTP server. The `main.py` entrypoint starts a NATS subscriber loop and runs until terminated. Liveness in Kubernetes is determined by process health, not an HTTP probe.

## Entry Point

`src/main.py` should:
1. Connect to NATS at `nats://nats.nats.svc.cluster.local:4222`
2. Subscribe to `incident.created` with a durable consumer
3. For each message: deserialize → run LangGraph workflow → publish result → ack message
4. Handle graceful shutdown on SIGTERM

## Dockerfile CMD

No uvicorn — override the pattern from root `CLAUDE.md`:
```dockerfile
CMD ["/venv/bin/python", "-m", "src.main"]
```

## OpenTelemetry

Apply `LoggingInstrumentor` only. There is no FastAPI app and no HTTP client to instrument. Export errors to the OTLP collector are non-fatal — do not remove instrumentation because of them.

## Testing

Mock OTel before importing any `src.*` module to avoid instrumentation side-effects:
```python
from unittest.mock import patch, MagicMock
with patch("opentelemetry.instrumentation.logging.LoggingInstrumentor"):
    from src.workflow import run_workflow
```
Mock `httpx.AsyncClient` to stub Ollama responses in node-level tests.
