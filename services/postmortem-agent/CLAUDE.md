# postmortem-agent

See the root `CLAUDE.md` for project-wide conventions (Dockerfile pattern, pyproject.toml, Helm naming, OTel setup, NATS topics).

## Role

Generates structured postmortem reports when incidents are resolved. Consumes both `incident.remediation.generated` (for the remediation context) and `incident.resolved` (as the trigger). Stores the report and logs it to stdout (future: persist to PostgreSQL).

## NATS

- **Subscribes to:** `incident.remediation.generated` AND `incident.resolved`
- **Publishes to:** nothing (terminal node in the event chain)
- **Consumer groups:**
  - `postmortem-agent-remediation` on `incident.remediation.generated`
  - `postmortem-agent-resolved` on `incident.resolved`

## State Correlation

This service consumes two separate NATS subjects for the same incident. It must correlate them by `incident_id`. Implementation approach for the stub:

- Maintain an in-memory dict keyed by `incident_id`
- When `incident.remediation.generated` arrives: store the remediation context
- When `incident.resolved` arrives: look up the stored remediation context, generate the postmortem, then clear the entry
- If `incident.resolved` arrives before `incident.remediation.generated`: wait (re-queue or hold in memory with a TTL)

Future: use Redis for correlation state to survive pod restarts.

## Input Models

**From `incident.remediation.generated`:**
```json
{
  "incident_id": "uuid",
  "rca_id": "uuid",
  "recommendations": [{"action": "string", "rationale": "string", "risk": "string"}],
  "generated_at": "ISO8601"
}
```

**From `incident.resolved`:**
```json
{
  "incident_id": "uuid",
  "resolved_at": "ISO8601",
  "resolution_summary": "string"
}
```

## Output Model (postmortem report — logged to stdout for now)

```json
{
  "incident_id": "uuid",
  "title": "string",
  "timeline": ["string"],
  "root_cause_summary": "string",
  "remediation_taken": ["string"],
  "action_items": ["string"],
  "generated_at": "ISO8601"
}
```

## LangGraph Workflow

StateGraph nodes in order:

1. **`build_timeline`** — Construct a timeline from the available timestamps (created_at, triaged_at, rca completed_at, remediation generated_at, resolved_at). Stub: derive from event timestamps.
2. **`generate_report`** — Prompt Ollama with the full incident context (root cause, remediation, resolution). Ask it to write a structured postmortem in JSON.
3. **`extract_action_items`** — Prompt Ollama to extract concrete follow-up action items from the postmortem narrative.
4. **`persist_report`** — Stub: log the final report to stdout as structured JSON. Future: INSERT into PostgreSQL `postmortems` table.

Edges: `build_timeline` → `generate_report` → `extract_action_items` → `persist_report`

## Ollama Usage

- **Model:** `llama3`
- **Endpoint:** `http://platform-ollama.platform.svc.cluster.local:11434`
- **Client:** `httpx.AsyncClient` POST to `/api/generate`

Example postmortem prompt:
```
You are an SRE writing a postmortem report. Based on the incident information below,
write a concise postmortem. Respond in JSON only.

Incident summary: {resolution_summary}
Root cause: {root_cause}
Remediation actions taken: {recommendations}

Respond with:
{
  "title": "string",
  "root_cause_summary": "string",
  "remediation_taken": ["string"],
  "action_items": ["string"]
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
2. Subscribe to both `incident.remediation.generated` and `incident.resolved` with separate durable consumers
3. Correlate events by `incident_id` using an in-memory dict
4. When both events are present for an `incident_id`: run LangGraph workflow → log report → clear state
5. Handle graceful shutdown on SIGTERM
