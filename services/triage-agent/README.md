# triage-agent

Classifies incoming incidents by severity, detects duplicates, and routes them downstream by publishing to `incident.triaged`.

**Event flow:** `incident.created` → **triage-agent** → `incident.triaged`

---

## Local Development

### Prerequisites

| Tool | Install |
|---|---|
| Python 3.14 | `brew install python@3.14` |
| Docker | [docker.com](https://www.docker.com/products/docker-desktop) |
| NATS CLI | `brew install nats-io/nats-tools/nats` |
| kubectl | already installed if you have the cluster |

---

### 1. Start NATS

```bash
docker run -d --name nats \
  -p 4222:4222 \
  -p 8222:8222 \
  nats:latest -js -m 8222
```

Verify it's up:
```bash
curl http://localhost:8222/healthz
# → {"status":"ok",...}
```

Create the JetStream stream (only needed once — survives container restarts if you keep the container):
```bash
nats stream add incidents \
  --subjects "incident.*" \
  --storage memory \
  --retention limits \
  --server localhost:4222
```

---

### 2. Start Ollama

If Ollama is installed locally, make sure it's running and the model is pulled:

```bash
ollama serve        # starts the server if not already running
ollama pull llama3  # only needed once
```

Verify it's up:
```bash
curl http://localhost:11434/api/tags
# → {"models":[{"name":"llama3",...}]}
```

> **Alternative — port-forward from the cluster** (if you don't have Ollama locally):
> ```bash
> kubectl port-forward -n platform svc/platform-ollama 11434:11434
> ```

---

### 3. Install the agent

```bash
cd services/triage-agent
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

### 4. Run the agent

```bash
NATS_URL=nats://localhost:4222 \
OLLAMA_URL=http://localhost:11434 \
python -m src.main
```

Expected output:
```
INFO triage-agent subscribed to incident.created
```

---

### 5. Send a test incident

In a new terminal, publish a sample `incident.created` event:

```bash
nats pub incident.created '{
  "id": "test-001",
  "title": "DB connection pool exhausted",
  "description": "Postgres hit max connections on prod",
  "severity": "unknown",
  "source": "api",
  "created_at": "2026-05-23T00:00:00Z"
}' --server localhost:4222
```

Try different severities to exercise the classifier:

```bash
# High severity
nats pub incident.created '{
  "id": "test-002",
  "title": "Payment service down",
  "description": "All payment requests returning 500, revenue impacted",
  "severity": "unknown",
  "source": "alertmanager",
  "created_at": "2026-05-23T00:00:00Z"
}' --server localhost:4222

# Low severity
nats pub incident.created '{
  "id": "test-003",
  "title": "Slow dashboard load",
  "description": "Admin dashboard taking 3s to load, no user impact",
  "severity": "unknown",
  "source": "api",
  "created_at": "2026-05-23T00:00:00Z"
}' --server localhost:4222
```

---

### 6. Verify the output

Subscribe to `incident.triaged` before sending a message to see what the agent publishes:

```bash
nats sub incident.triaged --server localhost:4222
```

Expected output shape:
```json
{
  "id": "test-001",
  "title": "DB connection pool exhausted",
  "description": "Postgres hit max connections on prod",
  "severity": "high",
  "source": "api",
  "assigned_team": "platform",
  "is_duplicate": false,
  "duplicate_of": null,
  "triaged_at": "2026-05-23T00:01:00Z"
}
```

---

### 7. Tear down

```bash
docker stop nats && docker rm nats
# Stop the kubectl port-forward with Ctrl+C
```

---

## Running Tests

```bash
cd services/triage-agent
source .venv/bin/activate
python -m pytest tests/ -v
```

Tests mock both Ollama and NATS — no running services needed.

---

## Environment Variables

| Variable | Default (in-cluster) | Local override |
|---|---|---|
| `NATS_URL` | `nats://nats-nats.nats.svc.cluster.local:4222` | `nats://localhost:4222` |
| `OLLAMA_URL` | `http://platform-ollama.platform.svc.cluster.local:11434` | `http://localhost:11434` |
