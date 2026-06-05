REGISTRY   ?= cloudnativeopsacr.azurecr.io
SERVICE    := remediation-agent
IMAGE      := $(REGISTRY)/$(SERVICE):latest
PLATFORM   ?= linux/amd64
NATS_URL   ?= nats://localhost:4222
OLLAMA_URL ?= http://localhost:11434

.PHONY: install test lint build push run

install:
	python3.14 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

test:
	.venv/bin/python -m pytest tests/ -v

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

build:
	docker buildx build --platform $(PLATFORM) -t $(IMAGE) .

push:
	docker buildx build --no-cache --platform $(PLATFORM) -t $(IMAGE) . --push

run:
	NATS_URL=$(NATS_URL) OLLAMA_URL=$(OLLAMA_URL) .venv/bin/python -m src.main
