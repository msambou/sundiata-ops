from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict

from pydantic import BaseModel, Field


class IncidentCreated(BaseModel):
    id: str
    title: str
    description: str
    severity: str = "unknown"
    source: str
    created_at: datetime


class IncidentTriaged(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    source: str
    assigned_team: str
    is_duplicate: bool
    duplicate_of: str | None
    triaged_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TriageState(TypedDict):
    id: str
    title: str
    description: str
    source: str
    created_at: str
    severity: str
    is_duplicate: bool
    duplicate_of: str | None
    assigned_team: str
