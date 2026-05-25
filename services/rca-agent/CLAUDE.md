# rca-agent

See the root `CLAUDE.md` for project-wide conventions (Dockerfile pattern, pyproject.toml, Helm naming, OTel setup, NATS topics).

## Role

Performs root cause analysis on triaged incidents by correlating logs, metrics, and traces. Publishes a structured RCA result to `incident.rca.completed`.

## NATS

- **Subscribes to:** `incident.triaged`
- **Publishes to:** `incident.rca.completed`
- **Consumer group:** `rca-agent` (durable, queue group)

## Input / Output Models

**Input** (from `incident.triaged`):
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "severity": "low | medium | high | critical",
  "source": "string",
  "assigned_team": "string",
  "triaged_at": "ISO8601"
}
```

**Output** (to `incident.rca.completed`):
```json
{
  "id": "uuid",
  "incident_id": "uuid",
  "root_cause": "string",
  "contributing_factors": ["string"],
  "affected_components": ["string"],
  "confidence": "low | medium | high",
  "evidence": ["string"],
  "completed_at": "ISO8601"
}
```

## LangGraph Workflow

StateGraph nodes in order:

1. **`gather_context`** — Stub: returns a synthetic context string built from the incident title + description. Future: query Loki for recent logs, Prometheus for anomalous metrics, Tempo for trace data.
2. **`analyze_root_cause`** — Prompt Ollama with the incident details + gathered context. Ask it to identify the most likely root cause and contributing factors. Parse into structured output.
3. **`identify_components`** — Prompt Ollama to list affected service/component names based on the RCA analysis.
4. **`publish_result`** — Serialize the RCA result and publish to `incident.rca.completed`.

Edges: `gather_context` → `analyze_root_cause` → `identify_components` → `publish_result`

## Ollama Usage

- **Model:** `llama3`
- **Endpoint:** `http://platform-ollama.platform.svc.cluster.local:11434`
- **Client:** `httpx.AsyncClient` POST to `/api/generate`

Example RCA prompt:
```
You are an SRE performing root cause analysis. Based on the incident below,
identify the root cause and contributing factors. Respond in JSON only.

Incident: {title}
Description: {description}
Severity: {severity}
Context: {context}

Respond with:
{
  "root_cause": "one sentence",
  "contributing_factors": ["factor1", "factor2"],
  "affected_components": ["component1"],
  "confidence": "low|medium|high"
}
```

## Key Dependencies

Beyond the common set in root `CLAUDE.md`:
- `langgraph>=0.4.0`
- `nats-py>=2.9.0`
- `httpx>=0.28.0`

## No HTTP Endpoints

Event-driven only. No FastAPI app. Liveness via process health.

## Entry Point

`src/main.py` should:
1. Connect to NATS at `nats://nats-nats.nats.svc.cluster.local:4222`
2. Subscribe to `incident.triaged` with a durable consumer
3. For each message: deserialize → run LangGraph workflow → publish RCA result → ack
4. Handle graceful shutdown on SIGTERM
