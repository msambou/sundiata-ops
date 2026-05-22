from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class IncidentRequest(BaseModel):
    title: str
    description: str
    severity: str = "unknown"
    source: str = "api"


class IncidentResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    severity: str
    source: str
    status: str = "created"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class HealthResponse(BaseModel):
    status: str
