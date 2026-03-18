import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    language: str
    description: str | None
    cookiecutter_url: str
    default_vars: dict | None
    created_at: datetime

class ScaffoldRequest(BaseModel):
    service_name: str
    team_id: str
    owner: str
    language: Literal["python", "go", "typescript", "rust", "java"]
    template: str = "python-fastapi"
    extra_vars: dict = {}
    repo_private: bool = True

class ScaffoldJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    service_name: str
    team_id: str
    owner: str
    language: str
    repo_url: str | None
    catalog_service_id: str | None
    compliance_score: int
    status: str
    temporal_workflow_id: str | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None
