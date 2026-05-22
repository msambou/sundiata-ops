# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sundiata Ops** is a cloud-native multi-agent incident response platform built on Kubernetes. It uses autonomous AI agents for incident detection, triage, root cause analysis, remediation, and postmortem reporting.

## Repository Status

| Layer | Status |
|---|---|
| `infrastructure/` | ✅ Complete — Terraform provisions AKS (Standard_D8s_v3 × 2, Kubernetes 1.35), ACR, resource group, AcrPull role assignment, and FluxCD bootstrap. Region: West US 2. |
| `gitops/` | ✅ Complete — Flux layer structure scaffolded; all platform Helm releases deployed (NATS, Kong, Ollama, kube-prometheus-stack, Loki); `incident-api` GitOps release live. |
| `helm/` | ✅ Partial — `helm/incident-api/` complete. Remaining service charts pending. |
| `services/` | ✅ Partial — `services/incident-api/` deployed and externally accessible via Kong. Remaining agents pending. |
| `platform/` | Planned — directory not yet created |
| CI/CD | Planned — Tekton pipelines |

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
├── flux-system/              # Auto-populated by Flux bootstrap — do not edit manually
├── kustomization.yaml        # Root entry point
├── infrastructure/
│   ├── sources/              # HelmRepository CRDs (NATS, Kong, Ollama, prometheus-community, Grafana)
│   └── releases/             # HelmRelease manifests
│       ├── kube-prometheus-stack.yaml   # monitoring namespace
│       ├── loki.yaml                    # monitoring namespace
│       ├── nats.yaml                    # nats namespace
│       ├── kong.yaml                    # kong namespace (DB-less mode)
│       └── ollama.yaml                  # platform namespace
└── apps/
    ├── kustomization.yaml
    └── incident-api/
        ├── kustomization.yaml
        └── helmrelease.yaml
```

Flux reconciles `infrastructure/` before `apps/` — platform dependencies are always up before services.

### Deployed Platform Components

| Component | Namespace | Chart Version | Notes |
|---|---|---|---|
| kube-prometheus-stack | `monitoring` | 85.2.0 | Prometheus + Grafana + Alertmanager |
| Loki | `monitoring` | 7.0.0 | SingleBinary mode, filesystem storage |
| NATS | `nats` | 2.14.0 | JetStream enabled, single broker |
| Kong | `kong` | 3.2.0 | DB-less mode, LoadBalancer proxy |
| Ollama | `platform` | 1.56.0 | CPU inference, llama3 + nomic-embed-text |

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

## Architecture

### Event Flow

```
incident.created → incident.triaged → incident.rca.completed
→ incident.remediation.generated → incident.resolved
```

### Core Services

| Service | Status | Role |
|---|---|---|
| `incident-api` | ✅ Deployed | FastAPI REST entry point; will emit `incident.created` events |
| `triage-agent` | Planned | Severity classification, deduplication, routing |
| `rca-agent` | Planned | Root cause analysis via logs/metrics/traces |
| `remediation-agent` | Planned | Recovery recommendations + Kubernetes actions |
| `notification-agent` | Planned | Slack/Teams alerts and escalation |
| `postmortem-agent` | Planned | Incident timelines and historical reporting |

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
│   ├── incident-api/   # ✅ Live
│   ├── triage-agent/   # Planned
│   ├── rca-agent/      # Planned
│   ├── remediation-agent/  # Planned
│   ├── notification-agent/ # Planned
│   └── postmortem-agent/   # Planned
├── docs/               # Architecture docs
└── scripts/            # Utility scripts
```

### Per-Service Directory Structure

Each directory under `services/<name>/` follows this layout:

```
services/<name>/
├── src/            # Application source (Python package)
├── tests/          # Unit and integration tests
├── Dockerfile
└── pyproject.toml  # Dependencies and tool config (ruff, mypy, pytest)
```

Kubernetes manifests live in `helm/<name>/` (Helm charts), not inside the service directory.
Each service must include OpenTelemetry instrumentation for traces, metrics, and logs.

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

Always include `packaging>=24.0` as an explicit dependency — `opentelemetry-instrumentation` requires it but doesn't always declare it.

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

### OpenTelemetry

The OTLP collector endpoint is `http://opentelemetry-collector.monitoring.svc.cluster.local:4317`. The collector is not yet deployed — export errors are expected and non-fatal (the SDK drops metrics silently). Do not remove OTel instrumentation because of these errors.

## Versioning Policy

Always use the latest stable versions of all tools, libraries, and platforms (Kubernetes, Terraform providers, Python packages, Helm charts, etc.). Before specifying any version, verify the current stable release. Never pin to an outdated version without an explicit reason from the user.

## Key Design Decisions

- **Self-hosted inference**: Ollama runs inside Kubernetes — never call external LLM APIs unless explicitly adding that capability.
- **Event-driven coupling**: Services communicate exclusively via NATS JetStream topics, not direct HTTP calls between agents.
- **GitOps deployment**: Changes to Kubernetes state go through FluxCD (commit → PR → merge → Flux reconciles). Never use `kubectl apply` directly.
- **Tekton for CI**: Build pipelines are Tekton-native (Kubernetes CRDs), not GitHub Actions or similar.
- **Kong DB-less**: Kong is configured via static declarative config in `gitops/infrastructure/releases/kong.yaml`. The Ingress Controller is disabled. Add new service routes to the `dblessConfig.config` block.
- **AKS LoadBalancer**: Do NOT set `service.beta.kubernetes.io/azure-load-balancer-resource-group` on LoadBalancer services. AKS manages load balancer resources in its own auto-generated node resource group and has no permissions over `cloudnative-ops-rg`.

## Development Commands

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

# Use --platform linux/amd64 if building on Apple Silicon
docker buildx build --no-cache --platform linux/amd64 \
  -t cloudnativeopsacr.azurecr.io/<service-name>:latest \
  services/<service-name>/ --push
```

AKS nodes already have AcrPull role (provisioned by Terraform) — no `imagePullSecret` needed.

### Forcing Flux reconciliation (no flux CLI required)

```bash
kubectl annotate kustomization flux-system \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --overwrite -n flux-system
```

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
