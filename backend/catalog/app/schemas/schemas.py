import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

ServiceHealth = Literal["healthy", "degraded", "frozen", "unknown"]
ServiceLang = Literal["python", "go", "typescript", "rust", "java", "other"]


class TeamCreate(BaseModel):
    name: str
    slug: str


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime


class ServiceCreate(BaseModel):
    name: str
    slug: str
    team_id: uuid.UUID
    owner: str
    language: ServiceLang | None = None
    repo_url: str | None = None
    description: str | None = None
    slo_uptime_target: float = Field(default=99.9, ge=0, le=100)
    slo_latency_p99_ms: int = Field(default=500, gt=0)
    tags: dict | None = None


class ServiceUpdate(BaseModel):
    name: str | None = None
    owner: str | None = None
    language: ServiceLang | None = None
    repo_url: str | None = None
    description: str | None = None
    slo_uptime_target: float | None = None
    slo_latency_p99_ms: int | None = None
    health_status: ServiceHealth | None = None
    current_version: str | None = None
    replica_count: int | None = None
    tags: dict | None = None


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    team_id: uuid.UUID
    owner: str
    language: ServiceLang | None
    repo_url: str | None
    description: str | None
    compliance_score: int
    maturity_score: int
    error_budget_consumed_pct: float
    deploy_frozen: bool
    health_status: ServiceHealth
    replica_count: int
    current_version: str | None
    last_deployed_at: datetime | None
    slo_uptime_target: float
    slo_latency_p99_ms: int
    tags: dict | None
    created_at: datetime
    updated_at: datetime


class ServiceListResponse(BaseModel):
    total: int
    services: list[ServiceResponse]


class CollectionCreate(BaseModel):
    name: str
    team_id: uuid.UUID | None = None
    filter_tags: dict | None = None
    service_ids: list[uuid.UUID] = []


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    team_id: uuid.UUID | None
    created_by: str
    created_at: datetime
    member_count: int = 0


class FleetOpRequest(BaseModel):
    operation: Literal["deploy", "rollback", "rescan", "patch"]
    service_ids: list[uuid.UUID]
    payload: dict = {}
    require_approval: bool = False


class FleetOpResponse(BaseModel):
    operation: str
    affected_services: int
    workflow_ids: list[str]
    status: str
