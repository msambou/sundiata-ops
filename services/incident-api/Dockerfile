# ── Stage 1: install dependencies into a venv ─────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install --upgrade pip

COPY pyproject.toml .
COPY src/ ./src/

RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install .

# ── Stage 2: runtime image ─────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home --shell /bin/false appuser

WORKDIR /app

COPY --from=builder /venv /venv
COPY src/ ./src/

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

ENV PATH="/venv/bin:$PATH"

CMD ["/venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
