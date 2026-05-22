from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .models import HealthResponse, IncidentRequest, IncidentResponse

OTLP_ENDPOINT = "http://opentelemetry-collector.monitoring.svc.cluster.local:4317"
SERVICE_NAME = "incident-api"

logger = logging.getLogger(__name__)


def configure_telemetry() -> None:
    resource = Resource.create({"service.name": SERVICE_NAME})

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True))
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Logs — inject trace context into log records
    LoggingInstrumentor().instrument(set_logging_format=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_telemetry()
    logger.info("incident-api started, telemetry configured")
    yield
    logger.info("incident-api shutting down")


app = FastAPI(title="incident-api", version="0.1.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/incidents", response_model=IncidentResponse, status_code=201, tags=["incidents"])
async def create_incident(body: IncidentRequest) -> IncidentResponse:
    tracer = trace.get_tracer(SERVICE_NAME)
    with tracer.start_as_current_span("create_incident") as span:
        incident = IncidentResponse(
            title=body.title,
            description=body.description,
            severity=body.severity,
            source=body.source,
        )
        span.set_attribute("incident.id", incident.id)
        span.set_attribute("incident.severity", incident.severity)
        logger.info("incident created", extra={"incident_id": incident.id})
        return incident
