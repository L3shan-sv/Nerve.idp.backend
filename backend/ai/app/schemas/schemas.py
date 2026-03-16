import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ChatRequest(BaseModel):
    message: str
    session_id: str
    incident_id: uuid.UUID | None = None
    service_id: str | None = None
    history: list[dict] = []

class ChatResponse(BaseModel):
    session_id: str
    response: str
    similar_incidents: list[dict] = []
    suggested_actions: list[str] = []

class IncidentCreate(BaseModel):
    service_id: str
    title: str
    severity: str = "P2"
    started_at: datetime

class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    service_id: str
    title: str
    severity: str
    root_cause: str | None
    resolution: str | None
    started_at: datetime
    resolved_at: datetime | None
    mttr_minutes: int | None
