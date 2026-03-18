import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

class IaCPlanRequest(BaseModel):
    service_id: str
    team_id: str
    tool: Literal["terraform", "pulumi"] = "terraform"
    module_path: str
    environment: Literal["development", "staging", "production"] = "staging"
    variables: dict = {}

class IaCPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    service_id: str
    team_id: str
    tool: str
    module_path: str
    environment: str
    diff_summary: str | None
    estimated_cost_delta_usd: float
    resources_to_add: int
    resources_to_change: int
    resources_to_destroy: int
    status: str
    approved_by: str | None
    approved_at: datetime | None
    temporal_workflow_id: str | None
    error: str | None
    created_by: str
    created_at: datetime
    applied_at: datetime | None

class IaCApprovalRequest(BaseModel):
    approved: bool
    approver: str
    reason: str | None = None
