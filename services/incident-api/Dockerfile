# ── Stage 1: install dependencies ─────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip hatchling

COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --prefix=/install .

# ── Stage 2: runtime image ─────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home --shell /bin/false appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ ./src/

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
