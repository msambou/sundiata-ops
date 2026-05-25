# notification-agent

See the root `CLAUDE.md` for project-wide conventions (Dockerfile pattern, pyproject.toml, Helm naming, OTel setup, NATS topics).

## Role

Sends incident notifications and escalation alerts to Slack/Teams when a remediation plan is generated. No LangGraph workflow — this is a simple event-to-webhook fan-out service.

## NATS

- **Subscribes to:** `incident.remediation.generated`
- **Publishes to:** nothing (terminal node in the event chain)
- **Consumer group:** `notification-agent` (durable, queue group)

## Input Model

**Input** (from `incident.remediation.generated`):
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

## Notification Targets (stub)

For the stub implementation, log the notification payload to stdout instead of calling real webhooks. The structure should be ready to swap in real webhook calls later.

Future integration points:
- **Slack:** `POST https://hooks.slack.com/services/...` with a Block Kit payload
- **Teams:** `POST https://outlook.office.com/webhook/...` with an Adaptive Card payload

Webhook URLs will be injected via environment variables (`SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`). Do not hardcode them.

## Workflow

No LangGraph needed — the logic is straightforward:

1. Deserialize the `incident.remediation.generated` event
2. Format a notification message (incident ID, top recommendation, risk level)
3. Send to configured channels (stub: log to stdout)
4. Ack the NATS message

## Key Dependencies

Beyond the common set in root `CLAUDE.md`:
- `nats-py>=2.9.0`
- `httpx>=0.28.0` — for future webhook POST calls

No `langgraph` dependency needed for this service.

## No HTTP Endpoints

Event-driven only. No FastAPI app. Liveness via process health.

## Entry Point

`src/main.py` should:
1. Connect to NATS at `nats://nats-nats.nats.svc.cluster.local:4222`
2. Subscribe to `incident.remediation.generated` with a durable consumer
3. For each message: deserialize → format notification → send (stub: log) → ack
4. Handle graceful shutdown on SIGTERM
