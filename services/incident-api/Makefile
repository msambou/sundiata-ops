REGISTRY ?= cloudnativeopsacr.azurecr.io
SERVICE  := incident-api
IMAGE    := $(REGISTRY)/$(SERVICE):latest
PLATFORM ?= linux/amd64

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
	.venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
