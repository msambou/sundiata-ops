# incident-api

See the root `CLAUDE.md` for project-wide conventions (Dockerfile pattern, pyproject.toml, Helm naming, OTel setup, safety rules).

## Role

FastAPI REST entry point for the platform. Accepts incident creation requests from external clients via Kong and returns a structured incident record. In the full implementation it will also publish to `incident.created` on NATS to kick off the agent chain.

## HTTP Endpoints

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/health` | — | `{"status": "ok"}` | 200 |
| POST | `/incidents` | `IncidentRequest` | `IncidentResponse` | 201 |

## Models (`src/models.py`)

**`IncidentRequest`** (POST body):
```python
title: str           # required
description: str     # required
severity: str = "unknown"
source: str = "api"
```

**`IncidentResponse`** (201 response):
```python
id: str              # UUID4, auto-generated
title: str
description: str
severity: str
source: str
status: str = "created"
created_at: datetime # UTC, auto-generated
```

**`HealthResponse`**:
```python
status: str
```

## OTel Instrumentation (`src/main.py`)

- `FastAPIInstrumentor.instrument_app(app)` — automatic span per request
- `LoggingInstrumentor` — injects trace context into log records
- `configure_telemetry()` called in the FastAPI `lifespan` context manager
- Span attributes set on `POST /incidents`: `incident.id`, `incident.severity`
- OTLP gRPC exporter → `http://opentelemetry-collector.monitoring.svc.cluster.local:4317`
- Collector not yet deployed — export errors are expected and non-fatal

## NATS (Not Yet Implemented)

This service will publish to `incident.created` after the incident record is created. When implementing:
- Add `nats-py>=2.9.0` to `pyproject.toml`
- Connect to `nats://nats-nats.nats.svc.cluster.local:4222` in the lifespan context manager
- Publish the serialized `IncidentResponse` to `incident.created` after the record is created in `POST /incidents`

## pyproject.toml Notes

- Must include `packaging>=24.0` — required by `opentelemetry-instrumentation` at runtime
- Must include `[tool.hatch.build.targets.wheel] packages = ["src"]` — hatchling won't find the package without this
- Build backend: `hatchling`

## Kong Routing

Externally accessible via Kong LoadBalancer. Routes declared in `gitops/infrastructure/releases/kong.yaml` under `dblessConfig.config`:
- `GET /health` → `http://apps-incident-api.apps.svc.cluster.local:8000`
- `POST /incidents` → `http://apps-incident-api.apps.svc.cluster.local:8000`

Note the service DNS is `apps-incident-api` not `incident-api` — see root `CLAUDE.md` for the Flux/Helm naming convention explanation.
