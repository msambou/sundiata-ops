# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sundiata Ops** is a cloud-native multi-agent incident response platform built on Kubernetes. It uses autonomous AI agents for incident detection, triage, root cause analysis, remediation, and postmortem reporting. The project is currently in the architecture/planning phase — comprehensive docs exist but microservice implementation is forthcoming.

## Repository Status

The repository currently contains documentation and configuration skeletons. No build commands, test suites, or CI/CD pipelines exist yet. When implementation begins, services will be Python (FastAPI) microservices.

## Architecture

### Event Flow

```
incident.created → incident.triaged → incident.rca.completed
→ incident.remediation.generated → incident.resolved
```

### Core Services (planned under `services/`)

| Service | Role |
|---|---|
| `incident-api` | FastAPI REST entry point; emits `incident.created` events |
| `triage-agent` | Severity classification, deduplication, routing |
| `rca-agent` | Root cause analysis via logs/metrics/traces |
| `remediation-agent` | Recovery recommendations + Kubernetes actions |
| `notification-agent` | Slack/Teams alerts and escalation |
| `postmortem-agent` | Incident timelines and historical reporting |

All agents share a **LangGraph + Ollama** stack. Ollama runs in-cluster (not an external API), serving as the shared LLM inference backend.

### Infrastructure Stack

| Layer | Technology |
|---|---|
| Cloud | Azure / AKS |
| IaC | Terraform (`infrastructure/`) |
| GitOps | FluxCD (`gitops/`) |
| Helm charts | `helm/` |
| Event bus | NATS JetStream |
| API gateway | Kong |
| Observability | Prometheus, Grafana, Loki, OpenTelemetry |
| Secrets | Azure Key Vault |
| Persistence | PostgreSQL + Redis |
| CI/CD | Tekton → ACR → FluxCD |

### Planned Directory Layout

```
sundiata-ops/
├── infrastructure/     # Terraform (AKS, ACR, Key Vault, networking)
├── gitops/             # FluxCD manifests
├── helm/               # Helm charts per service
├── platform/
│   ├── ollama/         # In-cluster LLM inference
│   ├── nats/           # Event streaming
│   ├── kong/           # API gateway config
│   ├── monitoring/     # Prometheus/Grafana stack
│   └── observability/  # OpenTelemetry collector config
├── services/
│   ├── incident-api/
│   ├── triage-agent/
│   ├── rca-agent/
│   ├── remediation-agent/
│   ├── notification-agent/
│   └── postmortem-agent/
├── docs/               # Architecture docs
└── scripts/            # Utility scripts
```

### Per-Service Directory Structure

Each directory under `services/<name>/` will follow this layout:

```
services/<name>/
├── src/            # Application source (Python package)
├── tests/          # Unit and integration tests
├── Dockerfile
└── pyproject.toml  # Dependencies and tool config (ruff, mypy, pytest)
```

Kubernetes manifests live in `helm/` (Helm charts), not inside the service directory.
Each service must include OpenTelemetry instrumentation for traces, metrics, and logs.

### Agent Implementation Pattern

Every agent service wraps its reasoning in a **LangGraph** `StateGraph`. The typical flow:

1. Subscribe to a NATS JetStream subject (e.g., `incident.triaged`)
2. Run the LangGraph workflow, calling Ollama for LLM inference
3. Publish the result to the next NATS subject (e.g., `incident.rca.completed`)

All LLM calls target the in-cluster Ollama service:
```
http://ollama.platform.svc.cluster.local:11434
```

Candidate models: Llama 3, Mistral, DeepSeek, Phi, Gemma.

### NATS Topic Conventions

Topics follow the pattern `incident.<lifecycle-stage>`:

| Topic | Publisher | Subscribers |
|---|---|---|
| `incident.created` | `incident-api` | `triage-agent` |
| `incident.triaged` | `triage-agent` | `rca-agent` |
| `incident.rca.completed` | `rca-agent` | `remediation-agent` |
| `incident.remediation.generated` | `remediation-agent` | `notification-agent`, `postmortem-agent` |
| `incident.resolved` | `remediation-agent` | `postmortem-agent` |

Services MUST NOT call each other directly over HTTP — all inter-service communication goes through NATS.

## Key Design Decisions

- **Self-hosted inference**: Ollama runs inside Kubernetes — never call external LLM APIs unless explicitly adding that capability.
- **Event-driven coupling**: Services communicate exclusively via NATS JetStream topics, not direct HTTP calls between agents.
- **GitOps deployment**: Changes to Kubernetes state go through FluxCD, not `kubectl apply` directly.
- **Tekton for CI**: Build pipelines are Tekton-native (Kubernetes CRDs), not GitHub Actions or similar.

## Development Commands

No build or test commands exist yet. Update this section as each service is scaffolded. The expected commands once `pyproject.toml` is in place for a service:

```bash
# Run from services/<name>/
python -m pytest                                    # all tests
python -m pytest tests/test_foo.py::test_bar        # single test
ruff check . && ruff format --check .               # lint
mypy src/                                           # type-check
uvicorn src.main:app --reload                       # local dev server (incident-api only)
```

## Safety Rules

### Absolute Restrictions

Claude MUST NOT:
- Modify infrastructure code, Kubernetes manifests, Terraform, Pulumi, Helm, Docker Compose, or deployment configs
- Access production systems, cloud consoles, CI/CD secrets, environment variable files, or secret managers
- Use or handle SSH keys, API keys, cloud credentials, or tokens
- Rotate, generate, or revoke credentials
- Run deployment commands (`kubectl`, `terraform`, `helm`, `aws`, `gcloud`, `az`, `flyctl`, `vercel`, `railway`, `docker login`, `ssh`, `scp`)
- Merge into protected branches or push directly to main/master
- Execute destructive commands

### Secret Handling

If a credential, token, private key, or sensitive env var is encountered: STOP immediately. Do NOT copy, use, store, or print it. Alert the user.

Sensitive examples: `.env` files, kubeconfig, cloud credentials, JWT/OAuth secrets, database URLs, API keys, private certificates.

### Allowed Actions

Claude MAY:
- Modify application code, add tests, refactor business logic, improve documentation
- Run local unit tests and static analysis
- Suggest infrastructure changes WITHOUT implementing them

### Infrastructure Change Workflow

If infrastructure changes are required:
1. Explain the required change and why
2. Provide the exact diff or command
3. Wait for explicit human approval — do NOT execute

### Git Restrictions

Claude MAY create commits and local branches.
Claude MUST NOT push to remote, force push, merge PRs, delete branches, or rewrite git history.
