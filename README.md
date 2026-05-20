# Sundiata Ops

A cloud-native multi-agent incident response platform built on Kubernetes.

Sundiata Ops leverages distributed AI agents, event-driven microservices, and GitOps workflows to autonomously detect, investigate, and remediate infrastructure incidents.

The platform is designed to simulate modern SRE and platform engineering workflows using autonomous AI agents, asynchronous messaging, and production-grade cloud-native tooling.

Unlike many AI platforms that rely on external hosted APIs, Sundiata Ops runs its LLM inference stack directly inside the Kubernetes cluster using Ollama, enabling fully self-hosted AI workflows within the platform.

---

# Project Goals

Sundiata Ops is built to demonstrate:

* Kubernetes-native architecture
* Distributed systems design
* Event-driven microservices
* Self-hosted LLM infrastructure
* AI agent orchestration
* GitOps deployment workflows
* Cloud-native observability
* Infrastructure as Code
* CI/CD automation
* Production-grade platform engineering practices

---

# High-Level Architecture

```text id="g5w3xw"
                           +----------------------+
                           |      API Gateway     |
                           |         Kong         |
                           +----------+-----------+
                                      |
                                      v
                         +------------+-------------+
                         |      Incident API        |
                         |        FastAPI           |
                         +------------+-------------+
                                      |
                                      v
                         +--------------------------+
                         |     NATS JetStream       |
                         |    Event Streaming Bus   |
                         +--------------------------+
                            |      |       |      |
                            |      |       |      |
              --------------       |       |      ----------------
             |                     |       |                     |
             v                     v       v                     v

      +-------------+     +-------------+    +-------------+   +-------------+
      | Triage      |     | RCA Agent   |    | Remediation |   | Notification|
      | Agent       |     |             |    | Agent       |   | Agent       |
      +------+------+     +------+------+    +------+------+   +------+------+
             |                     |                  |                 |
             ------------------------------------------------------------
                                      |
                                      v
                           +----------------------+
                           |  Postmortem Agent    |
                           +----------------------+

                                      |
                                      v

                           +----------------------+
                           |   Ollama Inference   |
                           |      Service         |
                           +----------------------+
```

---

# Core Architecture Principles

## Event-Driven Communication

Services communicate asynchronously through NATS JetStream using publish/subscribe patterns.

Example event lifecycle:

```text id="m56p6v"
incident.created
    ↓
incident.triaged
    ↓
incident.rca.completed
    ↓
incident.remediation.generated
    ↓
incident.resolved
```

This approach enables:

* loose coupling
* horizontal scalability
* resiliency
* fault isolation
* independent deployments

---

# AI Agent System

Each agent is implemented as an independent microservice deployed on Kubernetes.

Internally, agents use LangGraph workflows to orchestrate reasoning and decision-making pipelines.

All agents consume inference from a centralized Ollama inference service deployed within the cluster.

## Triage Agent

Responsible for:

* severity classification
* ownership routing
* incident prioritization
* duplicate detection

## RCA Agent

Responsible for:

* log analysis
* metrics correlation
* trace inspection
* root cause identification

## Remediation Agent

Responsible for:

* remediation recommendations
* Kubernetes recovery actions
* scaling suggestions
* rollback strategies

## Notification Agent

Responsible for:

* Slack notifications
* Teams alerts
* incident communications
* escalation workflows

## Postmortem Agent

Responsible for:

* incident timelines
* postmortem generation
* incident summaries
* historical reporting

---

# Self-Hosted LLM Infrastructure

Sundiata Ops runs LLM inference directly inside the Kubernetes cluster using Ollama.

This enables:

* self-hosted AI workloads
* reduced external API dependency
* local inference experimentation
* infrastructure-level AI observability
* portable AI deployments

The inference layer is deployed as an internal Kubernetes service and shared across all agents.

Potential models include:

* Llama 3
* DeepSeek
* Mistral
* Phi
* Gemma

Future enhancements may include:

* GPU node pools
* inference autoscaling
* model routing
* multi-model orchestration
* vLLM integration

---

# Cloud-Native Stack

| Concern                   | Technology               |
| ------------------------- | ------------------------ |
| Cloud Provider            | Azure                    |
| Kubernetes                | AKS                      |
| Infrastructure as Code    | Terraform                |
| API Gateway               | Kong                     |
| Event Streaming           | NATS JetStream           |
| GitOps                    | FluxCD                   |
| CI/CD                     | Tekton                   |
| AI Workflow Orchestration | LangGraph                |
| LLM Inference             | Ollama                   |
| Observability             | Prometheus + Grafana     |
| Distributed Tracing       | OpenTelemetry            |
| Logging                   | Loki                     |
| Container Registry        | Azure Container Registry |
| Secrets Management        | Azure Key Vault          |
| Persistence               | PostgreSQL / Redis       |

---

# Infrastructure Provisioning

Infrastructure is provisioned declaratively using Terraform.

Terraform manages:

* AKS clusters
* networking
* Azure Container Registry
* Azure Key Vault
* monitoring resources
* managed identities
* storage resources
* Ollama infrastructure resources

Infrastructure changes are version-controlled and reproducible.

---

# GitOps Workflow

Sundiata Ops follows a GitOps deployment model powered by FluxCD.

Deployment pipeline:

```text id="7wy5ao"
Git Push
   ↓
Tekton Pipeline
   ↓
Build & Test
   ↓
Push Image to ACR
   ↓
Update GitOps Repository
   ↓
FluxCD Reconciliation
   ↓
Deployment to AKS
```

All deployments are managed declaratively through Git.

---

# Observability

The platform is fully instrumented for production-grade observability.

## Metrics

Prometheus collects:

* incident metrics
* agent processing latency
* inference latency
* queue metrics
* infrastructure metrics

## Logs

Loki aggregates centralized logs across all services.

## Distributed Tracing

OpenTelemetry traces requests across the entire incident lifecycle.

Example trace path:

```text id="vvq8yj"
Incident API
   ↓
NATS
   ↓
Triage Agent
   ↓
Ollama
   ↓
RCA Agent
   ↓
Remediation Agent
```

---

# Repository Structure

```text id="qpd72u"
sundiata-ops/
│
├── infrastructure/        # Terraform infrastructure
├── gitops/                # FluxCD manifests
├── helm/                  # Helm charts
├── docs/                  # Architecture documentation
├── scripts/               # Utility scripts
│
├── platform/
│   ├── ollama/
│   ├── nats/
│   ├── kong/
│   ├── monitoring/
│   └── observability/
│
├── services/
│   ├── incident-api/
│   ├── triage-agent/
│   ├── rca-agent/
│   ├── remediation-agent/
│   ├── notification-agent/
│   └── postmortem-agent/
│
└── README.md
```

Each microservice contains:

* isolated source code
* Dockerfile
* Kubernetes manifests
* service-specific README
* tests
* observability instrumentation

---

# Engineering Focus Areas

Sundiata Ops emphasizes:

* distributed microservices
* asynchronous event processing
* Kubernetes platform engineering
* self-hosted AI infrastructure
* AI-assisted operations
* cloud-native resiliency patterns
* scalable observability
* infrastructure automation
* production deployment workflows

---

# Future Enhancements

Planned enhancements include:

* automated remediation execution
* GPU-backed inference pools
* inference autoscaling
* chaos engineering experiments
* service mesh integration
* canary deployments
* KEDA autoscaling
* multi-cluster deployments
* anomaly detection pipelines
* policy-driven remediation workflows

---

# Vision

Sundiata Ops is an exploration of how autonomous AI systems can augment modern platform engineering and incident response workflows in cloud-native environments while leveraging fully self-hosted LLM infrastructure on Kubernetes.
