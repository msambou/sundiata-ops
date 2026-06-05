# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sundiata Ops** is a cloud-native multi-agent incident response platform built on Kubernetes. It uses autonomous AI agents for incident detection, triage, root cause analysis, remediation, and postmortem reporting.

## Repository Status

| Layer | Status |
|---|---|
| `infrastructure/` | ✅ Complete — Terraform provisions AKS (Standard_D8s_v3 × 2, Kubernetes 1.35), ACR, resource group, AcrPull role assignment, and FluxCD bootstrap. Region: West US 2. |
| `gitops/` | ✅ Partial — Layered Kustomization structure (infrastructure → apps); all platform Helm releases deployed; `incident-api` and `triage-agent` GitOps releases live; `nats-streams.yaml` Job live (creates `incidents` JetStream stream before agents start). |
| `helm/` | ✅ Partial — `helm/incident-api/` and `helm/triage-agent/` complete. Remaining service charts pending. |
| `services/` | ✅ Partial — `incident-api` deployed via Kong (NATS publish not yet wired); `triage-agent` deployed and running; remaining agents have `CLAUDE.md` + `Makefile` only. |
| CI/CD | 🔜 Next priority — Tekton pipelines (install Tekton, build pipeline per service: lint → test → docker build → push to ACR → update HelmRelease image tag) |
| `platform/` | Planned — directory not yet created |

### Implementation Roadmap (ordered)

| Step | Work | Status |
|---|---|---|
| 1 | Merge `triage-agent` branch → `main`; push image with `make push SERVICE=triage-agent` | ✅ Done |
| 2 | Install Tekton on AKS; scaffold build pipeline (lint → test → build → push → update image tag) | 🔜 Next priority |
| 3 | Wire `incident-api` NATS publish to `incident.created` | Blocked on step 2 |
| 4 | Scaffold `rca-agent` (Python + Helm + GitOps) | Pending |
| 5 | Scaffold `remediation-agent` | Pending |
| 6 | Scaffold `notification-agent` | Pending |
| 7 | Scaffold `postmortem-agent` | Pending |

### Infrastructure Details

- **Terraform files:** `infrastructure/` — `providers.tf`, `variables.tf`, `main.tf`, `outputs.tf`, `flux.tf`
- **AKS cluster:** `cloudnative-ops-aks`, resource group `cloudnative-ops-rg`, West US 2
- **Node pool:** `Standard_D8s_v3 × 2` (system workloads + Ollama CPU inference)
- **ACR:** `cloudnativeopsacr`
- **FluxCD:** bootstrapped via `fluxcd/flux` Terraform provider; watches the `gitops/` path on `main`
- **GitHub owner:** `msambou` — only CODEOWNER (`.github/CODEOWNERS`)
- **Secret handling:** `github_token` is never stored in `.tfvars` — passed via `TF_VAR_github_token` env var at apply time

### GitOps Layer

```
gitops/
├── flux-system/                       # Auto-populated by Flux bootstrap — do not edit manually
├── kustomization.yaml                 # Root: manages flux-system + two child Kustomization CRs
├── infrastructure-kustomization.yaml  # Flux Kustomization CR — infra layer (healthChecks: otel-operator)
├── apps-kustomization.yaml            # Flux Kustomization CR — apps layer (dependsOn: infrastructure)
├── infrastructure/
│   ├── kustomization.yaml
│   ├── sources/              # HelmRepository CRDs (NATS, Kong, Ollama, prometheus-community, Grafana, OTel)
│   └── releases/             # HelmRelease manifests
│       ├── kube-prometheus-stack.yaml   # monitoring namespace
│       ├── loki.yaml                    # monitoring namespace
│       ├── nats.yaml                    # nats namespace
│       ├── kong.yaml                    # kong namespace (DB-less mode)
│       ├── ollama.yaml                  # platform namespace
│       └── opentelemetry-operator.yaml  # monitoring namespace
└── apps/
    ├── kustomization.yaml
    ├── instrumentation/      # Instrumentation CR (opentelemetry.io/v1alpha1) covering apps namespace
    ├── incident-api/
    │   ├── kustomization.yaml
    │   └── helmrelease.yaml
    └── triage-agent/
        ├── kustomization.yaml
        └── helmrelease.yaml
```

The root Kustomization (`flux-system`) creates two child Kustomization objects. `infrastructure` health-checks the `opentelemetry-operator` HelmRelease before reporting Ready. `apps` has `dependsOn: infrastructure` so it only starts after OTel Operator CRDs are registered — this prevents the `Instrumentation` CR dry-run from failing on a missing CRD.

### Deployed Platform Components

| Component | Namespace | Chart Version | Notes |
|---|---|---|---|
| kube-prometheus-stack | `monitoring` | 85.2.0 | Prometheus + Grafana + Alertmanager |
| Loki | `monitoring` | 7.0.0 | SingleBinary mode, filesystem storage |
| NATS | `nats` | 2.14.0 | JetStream enabled, single broker |
| Kong | `kong` | 3.2.0 | DB-less mode, LoadBalancer proxy |
| Ollama | `platform` | 1.56.0 | CPU inference, llama3 + nomic-embed-text |
| opentelemetry-operator | `monitoring` | 0.113.1 | Injects OTel auto-instrumentation via pod annotations |

### Kong DB-less Configuration

Kong runs in DB-less mode (`env.database: "off"`). All routes are declared statically in `gitops/infrastructure/releases/kong.yaml` under `dblessConfig.config`. When adding a new service, add its upstream and routes there.

**Current routes:**
- `GET /health` → `apps-incident-api.apps.svc.cluster.local:8000`
- `POST /incidents` → `apps-incident-api.apps.svc.cluster.local:8000`

## ⚠️ Helm + Flux Service Naming Convention

**This has caused debugging pain and must be understood before writing any service discovery config.**

When a HelmRelease has `storageNamespace` set to a value other than `flux-system`, Flux uses `<storageNamespace>-<helmReleaseName>` as the Helm release name. This prefixes **all** Kubernetes resources created by the chart (Deployments, Services, etc.).

**Example:**
```yaml
# gitops/apps/incident-api/helmrelease.yaml
metadata:
  name: incident-api          # HelmRelease name
  namespace: flux-system
spec:
  targetNamespace: apps
  storageNamespace: apps      # ← triggers the prefix
```

Flux installs this as Helm release name `apps-incident-api`, so:
- **Deployment name:** `apps-incident-api`
- **Service name:** `apps-incident-api`
- **DNS:** `apps-incident-api.apps.svc.cluster.local`

**Rule:** When referencing a service from Kong DB-less config, NATS, or any other service discovery, always use `<storageNamespace>-<helmReleaseName>.<targetNamespace>.svc.cluster.local` — never just `<helmReleaseName>.<targetNamespace>.svc.cluster.local`.

**To verify the actual service name after deploy:**
```bash
kubectl get svc -n <targetNamespace>
```

### Known cluster service DNS names

| HelmRelease | `storageNamespace` | Actual service DNS |
|---|---|---|
| `nats` | `nats` | `nats-nats.nats.svc.cluster.local:4222` |
| `ollama` | `platform` | `platform-ollama.platform.svc.cluster.local:11434` |
| `kong` | `kong` | `kong-kong-proxy.kong.svc.cluster.local` |
| `incident-api` | `apps` | `apps-incident-api.apps.svc.cluster.local:8000` |
| `triage-agent` | `apps` | `apps-triage-agent.apps.svc.cluster.local` (no HTTP — event-driven only) |

Always verify with `kubectl get svc -n <namespace>` after a new deploy.

## Architecture

### Event Flow

```
incident.created → incident.triaged → incident.rca.completed
→ incident.remediation.generated → incident.resolved
```

### Core Services

| Service | Status | Role |
|---|---|---|
| `incident-api` | ✅ Deployed | FastAPI REST entry point; receives `POST /incidents` via Kong. **NATS publish (`incident.created`) not yet wired** — planned after Tekton CI is set up. |
| `triage-agent` | ✅ Deployed | Severity classification, deduplication, team routing. Subscribes `incident.created` → publishes `incident.triaged`. |
| `rca-agent` | 🔜 Scaffolding pending | Root cause analysis via logs/metrics/traces. `CLAUDE.md` + `Makefile` exist; no Python code yet. |
| `remediation-agent` | 🔜 Scaffolding pending | Recovery recommendations + Kubernetes actions. `CLAUDE.md` + `Makefile` exist; no Python code yet. |
| `notification-agent` | 🔜 Scaffolding pending | Slack/Teams alerts and escalation. `CLAUDE.md` + `Makefile` exist; no Python code yet. |
| `postmortem-agent` | 🔜 Scaffolding pending | Incident timelines and historical reporting. `CLAUDE.md` + `Makefile` exist; no Python code yet. |

All agents share a **LangGraph + Ollama** stack. Ollama runs in-cluster (not an external API), serving as the shared LLM inference backend.

### Infrastructure Stack

| Layer | Technology |
|---|---|
| Cloud | Azure / AKS |
| IaC | Terraform (`infrastructure/`) |
| GitOps | FluxCD (`gitops/`) |
| Helm charts | `helm/` |
| Event bus | NATS JetStream |
| API gateway | Kong (DB-less) |
| Observability | Prometheus, Grafana, Loki, OpenTelemetry |
| Secrets | Azure Key Vault |
| Persistence | PostgreSQL + Redis |
| CI/CD | Tekton → ACR → FluxCD |

### Directory Layout

```
sundiata-ops/
├── infrastructure/     # Terraform (AKS, ACR, Key Vault, networking) — DO NOT EDIT
├── gitops/             # FluxCD manifests
├── helm/               # Helm charts per service
├── platform/           # Planned — platform config (not yet created)
├── services/
│   ├── incident-api/   # ✅ Live — NATS publish pending
│   ├── triage-agent/   # ✅ Deployed
│   ├── rca-agent/      # 🔜 CLAUDE.md + Makefile only
│   ├── remediation-agent/  # 🔜 CLAUDE.md + Makefile only
│   ├── notification-agent/ # 🔜 CLAUDE.md + Makefile only
│   └── postmortem-agent/   # 🔜 CLAUDE.md + Makefile only
├── docs/               # Architecture docs
├── scripts/            # Utility scripts
└── Makefile            # Root make targets: push, build, test, lint, run (per-service + all variants)
```

### Per-Service Directory Structure

Each directory under `services/<name>/` follows this layout:

```
services/<name>/
├── src/            # Application source (Python package)
├── tests/          # Unit and integration tests
├── Dockerfile
├── Makefile        # Per-service build/push/test/run targets
└── pyproject.toml  # Dependencies and tool config (ruff, mypy, pytest)
```

Kubernetes manifests live in `helm/<name>/` (Helm charts), not inside the service directory.
OTel instrumentation is handled by the OpenTelemetry Operator via pod annotation — no SDK code in services.

### Dockerfile Pattern

Use the venv multi-stage pattern (see `services/incident-api/Dockerfile` as the reference):
- **Stage 1 (builder):** `python:3.14-slim`, create `/venv`, install deps via `pip install .`
- **Stage 2 (runtime):** `python:3.14-slim`, copy `/venv` from builder, copy `src/`, non-root user (uid=1001)
- `CMD ["/venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]`

Do NOT use `pip install --prefix=` — use venv instead.

### pyproject.toml Pattern

Use `hatchling` as the build backend. Always include:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src"]
```
This is required because hatchling defaults to looking for a directory named after the project, which won't match when the project name contains hyphens.

### Agent Implementation Pattern

Every agent service wraps its reasoning in a **LangGraph** `StateGraph`. The typical flow:

1. Subscribe to a NATS JetStream subject (e.g., `incident.triaged`)
2. Run the LangGraph workflow, calling Ollama for LLM inference
3. Publish the result to the next NATS subject (e.g., `incident.rca.completed`)

All LLM calls target the in-cluster Ollama service:
```
http://platform-ollama.platform.svc.cluster.local:11434
```

NATS connect URL:
```
nats://nats-nats.nats.svc.cluster.local:4222
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

### OpenTelemetry

Instrumentation is injected by the **OpenTelemetry Operator** — do NOT add OTel SDK code to service source. Application code contains only business logic.

To enable injection for a service, add to `helm/<service>/values.yaml`:
```yaml
podAnnotations:
  instrumentation.opentelemetry.io/inject-python: "true"
env:
  - name: OTEL_SERVICE_NAME
    value: "<service-name>"
```

The `Instrumentation` CR lives at `gitops/apps/instrumentation/instrumentation.yaml` and covers the entire `apps` namespace. The OTLP endpoint is `http://opentelemetry-collector.monitoring.svc.cluster.local:4317`.

### Logging Best Practice

**Always call `logging.basicConfig(level=logging.INFO)` in every service's `main.py`.** The OTel operator injects auto-instrumentation that exports logs to the collector, but it is an *exporter* — it only processes log records that Python's logging system actually emits. Python's root logger defaults to `WARNING`, silently dropping all `INFO` logs before OTel ever sees them.

Each layer has a distinct responsibility:

| Layer | Responsibility |
|---|---|
| `logging.basicConfig(level=INFO)` | Controls which log records Python emits |
| OTel `LoggingInstrumentor` (injected) | Injects trace/span IDs into log records |
| OTel collector | Ships logs to Loki |

Without `basicConfig(level=INFO)`, startup messages, business events, and processing logs are all silently dropped. Only errors appear. Every service must set this explicitly — never rely on the Python default.

## Versioning Policy

Always use the latest stable versions of all tools, libraries, and platforms (Kubernetes, Terraform providers, Python packages, Helm charts, etc.). Before specifying any version, verify the current stable release. Never pin to an outdated version without an explicit reason from the user.

## Key Design Decisions

- **Self-hosted inference**: Ollama runs inside Kubernetes — never call external LLM APIs unless explicitly adding that capability.
- **Event-driven coupling**: Services communicate exclusively via NATS JetStream topics, not direct HTTP calls between agents.
- **GitOps deployment**: Changes to Kubernetes state go through FluxCD (commit → PR → merge → Flux reconciles). Never use `kubectl apply` directly.
- **Tekton for CI**: Build pipelines are Tekton-native (Kubernetes CRDs), not GitHub Actions or similar. Until Tekton pipelines are in place, per-service `Makefile` targets (`make push SERVICE=<name>`) serve as the manual CI bridge.
- **Kong DB-less**: Kong is configured via static declarative config in `gitops/infrastructure/releases/kong.yaml`. The Ingress Controller is disabled. Add new service routes to the `dblessConfig.config` block.
- **AKS LoadBalancer**: Do NOT set `service.beta.kubernetes.io/azure-load-balancer-resource-group` on LoadBalancer services. AKS manages load balancer resources in its own auto-generated node resource group and has no permissions over `cloudnative-ops-rg`.

## Development Commands

### Makefile targets (preferred)

Every service has a `Makefile` with standard targets. Use these instead of raw commands.

```bash
# Single service (run from repo root)
make build  SERVICE=triage-agent    # docker buildx build (no push)
make push   SERVICE=triage-agent    # docker buildx build --push to ACR
make test   SERVICE=triage-agent    # pytest
make lint   SERVICE=triage-agent    # ruff check + format --check
make run    SERVICE=triage-agent    # run locally with NATS_URL / OLLAMA_URL

# All services at once
make build-all
make push-all
make test-all
make lint-all

# Override vars
make run SERVICE=triage-agent NATS_URL=nats://localhost:4222 OLLAMA_URL=http://localhost:11434
make push SERVICE=triage-agent PLATFORM=linux/arm64
```

Variables available per-service:

| Variable | Default | Notes |
|---|---|---|
| `REGISTRY` | `cloudnativeopsacr.azurecr.io` | ACR registry prefix |
| `PLATFORM` | `linux/amd64` | Override to `linux/arm64` for Apple Silicon local builds |
| `NATS_URL` | `nats://localhost:4222` | Local NATS for `make run` |
| `OLLAMA_URL` | `http://localhost:11434` | Local Ollama for `make run` (LangGraph agents only) |

**`notification-agent` has no `OLLAMA_URL`** — it uses no LangGraph/Ollama.

### Raw commands (use when not at repo root)

```bash
# Run from services/<name>/
python -m pytest                                    # all tests
python -m pytest tests/test_foo.py::test_bar        # single test
ruff check . && ruff format --check .               # lint
mypy src/                                           # type-check
uvicorn src.main:app --reload                       # local dev server (incident-api only)
```

### Building and pushing a service image to ACR

```bash
az acr login --name cloudnativeopsacr

# Preferred: use Makefile
make push SERVICE=<service-name>

# Manual equivalent (Apple Silicon → linux/amd64)
docker buildx build --no-cache --platform linux/amd64 \
  -t cloudnativeopsacr.azurecr.io/<service-name>:latest \
  services/<service-name>/ --push
```

AKS nodes already have AcrPull role (provisioned by Terraform) — no `imagePullSecret` needed.

### Forcing Flux reconciliation (no flux CLI required)

```bash
# Root kustomization
kubectl annotate kustomization flux-system \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --overwrite -n flux-system

# Child kustomizations (force individually when needed)
kubectl annotate kustomization infrastructure \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --overwrite -n flux-system

kubectl annotate kustomization apps \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --overwrite -n flux-system
```

**Important:** Annotating a Kustomization only re-applies the HelmRelease *object* — it does NOT force the Helm controller to upgrade the chart. To force a chart upgrade, annotate the HelmRelease directly:

```bash
kubectl annotate helmrelease <name> \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --overwrite -n flux-system
```

### Recovering a stalled HelmRelease

A HelmRelease enters `Stalled` state when a Helm upgrade fails AND there is no previous successful release to roll back to. Flux stops retrying. Symptom:

```
message: 'Failed to perform remediation: missing target release for rollback: cannot remediate failed release'
reason: MissingRollbackTarget
type: Stalled
```

**Fix — suspend and resume to force a fresh install:**

```bash
kubectl patch helmrelease <name> -n flux-system \
  --type=merge -p '{"spec":{"suspend":true}}'

kubectl patch helmrelease <name> -n flux-system \
  --type=merge -p '{"spec":{"suspend":false}}'

kubectl annotate helmrelease <name> \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --overwrite -n flux-system
```

**Prevention:** ensure the chart values are correct (especially DNS names — see Helm + Flux naming convention above) before the first deploy. A pod that crashes on startup due to a wrong env var will fail the Helm upgrade health check and trigger this stalled state.

## Safety Rules

### Absolute Restrictions

Claude MUST NOT:
- Modify files in `infrastructure/` (Terraform) — suggest changes and wait for human approval
- Access production systems, cloud consoles, CI/CD secrets, environment variable files, or secret managers
- Use or handle SSH keys, API keys, cloud credentials, or tokens
- Rotate, generate, or revoke credentials
- Run deployment commands against live systems (`kubectl apply`, `terraform apply`, `helm install`, `aws`, `gcloud`, `az`, `docker login`, `ssh`, `scp`)
- Merge into protected branches or push directly to main/master
- Execute destructive commands

### Secret Handling

If a credential, token, private key, or sensitive env var is encountered: STOP immediately. Do NOT copy, use, store, or print it. Alert the user.

Sensitive examples: `.env` files, kubeconfig, cloud credentials, JWT/OAuth secrets, database URLs, API keys, private certificates.

### Allowed Actions

Claude MAY:
- Modify application code in `services/`, add tests, refactor business logic
- Modify Helm charts in `helm/`
- Modify GitOps manifests in `gitops/` (HelmReleases, Kustomizations, HelmRepositories)
- Run local unit tests and static analysis
- Read-only `kubectl get/describe/logs` commands for debugging

### Infrastructure Change Workflow

If `infrastructure/` (Terraform) changes are required:
1. Explain the required change and why
2. Provide the exact diff or command
3. Wait for explicit human approval — do NOT execute
