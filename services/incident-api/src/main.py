from __future__ import annotations

import logging

from fastapi import FastAPI

from .models import HealthResponse, IncidentRequest, IncidentResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="incident-api", version="0.1.0")


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/incidents",
    response_model=IncidentResponse,
    status_code=201,
    tags=["incidents"],
)
async def create_incident(body: IncidentRequest) -> IncidentResponse:
    incident = IncidentResponse(
        title=body.title,
        description=body.description,
        severity=body.severity,
        source=body.source,
    )
    logger.info("incident created", extra={"incident_id": incident.id})
    return incident
