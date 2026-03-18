import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class PipelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    service_id: str
    repo_full_name: str
    workflow_name: str
    run_id: int
    run_number: int
    branch: str
    commit_sha: str
    actor: str
    status: str
    conclusion: str | None
    duration_seconds: int | None
    stages: list | None
    html_url: str | None
    started_at: datetime
    completed_at: datetime | None

class PipelineListResponse(BaseModel):
    total: int
    pipelines: list[PipelineResponse]

class PipelineSyncRequest(BaseModel):
    service_id: str
    repo_full_name: str
    limit: int = 20
