# remediation-agent

See the root `CLAUDE.md` for project-wide conventions (Dockerfile pattern, pyproject.toml, Helm naming, OTel setup, NATS topics).

## Role

Generates remediation recommendations based on the RCA result, optionally executes safe Kubernetes recovery actions (restarts, scaling), and publishes to both `incident.remediation.generated` and `incident.resolved`.

## NATS

- **Subscribes to:** `incident.rca.completed`
- **Publishes to:** `incident.remediation.generated` AND `incident.resolved`
- **Consumer group:** `remediation-agent` (durable, queue group)

## Input / Output Models

**Input** (from `incident.rca.completed`):
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

**Output to `incident.remediation.generated`:**
```json
{
  "incident_id": "uuid",
  "rca_id": "uuid",
  "recommendations": [
    {
      "action": "string",
      "rationale": "string",
      "risk": "low | medium | high",
      "automated": false
    }
  ],
  "generated_at": "ISO8601"
}
```

**Output to `incident.resolved`:**
```json
{
  "incident_id": "uuid",
  "resolved_at": "ISO8601",
  "resolution_summary": "string"
}
```

## LangGraph Workflow

StateGraph nodes in order:

1. **`generate_recommendations`** — Prompt Ollama with the RCA result. Ask it to produce a ranked list of remediation actions with risk levels.
2. **`evaluate_automation`** — For each recommendation, determine if it is safe to automate (stub: always returns `automated: false`). Future: apply a policy ruleset.
3. **`publish_remediation`** — Publish the remediation recommendations to `incident.remediation.generated`.
4. **`publish_resolved`** — Publish a resolution summary to `incident.resolved`.

Edges: `generate_recommendations` → `evaluate_automation` → `publish_remediation` → `publish_resolved`

Both `publish_remediation` and `publish_resolved` must complete before the workflow ends — they are sequential, not parallel, because `incident.resolved` should only fire after the remediation plan is published.

## Ollama Usage

- **Model:** `llama3`
- **Endpoint:** `http://ollama.platform.svc.cluster.local:11434`
- **Client:** `httpx.AsyncClient` POST to `/api/generate`

Example remediation prompt:
```
You are an SRE recommending remediation steps. Based on the root cause analysis below,
suggest a prioritized list of remediation actions. Respond in JSON only.

Root cause: {root_cause}
Affected components: {affected_components}
Confidence: {confidence}

Respond with:
{
  "recommendations": [
    {"action": "string", "rationale": "string", "risk": "low|medium|high"}
  ]
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
1. Connect to NATS at `nats://nats.nats.svc.cluster.local:4222`
2. Subscribe to `incident.rca.completed` with a durable consumer
3. For each message: deserialize → run LangGraph workflow → ack
4. Handle graceful shutdown on SIGTERM
