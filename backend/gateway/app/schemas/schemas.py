import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Team ────────────────────────────────────────────────────

class TeamBase(BaseModel):
    name: str
    slug: str


class TeamCreate(TeamBase):
    pass


class TeamResponse(TeamBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


# ── Service ─────────────────────────────────────────────────

ServiceHealth = Literal["healthy", "degraded", "frozen", "unknown"]
ServiceLang = Literal["python", "go", "typescript", "rust", "java", "other"]


class ServiceBase(BaseModel):
    name: str
    slug: str
    owner: str
    language: ServiceLang | None = None
    repo_url: str | None = None
    description: str | None = None
    slo_uptime_target: float = Field(default=99.9, ge=0, le=100)
    slo_latency_p99_ms: int = Field(default=500, gt=0)


class ServiceCreate(ServiceBase):
    team_id: uuid.UUID


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


class ServiceResponse(ServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    compliance_score: int
    maturity_score: int
    error_budget_consumed_pct: float
    deploy_frozen: bool
    health_status: ServiceHealth
    replica_count: int
    current_version: str | None
    last_deployed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ServiceListResponse(BaseModel):
    total: int
    services: list[ServiceResponse]


# ── Deploy ──────────────────────────────────────────────────

class DeployRequest(BaseModel):
    service_id: uuid.UUID
    image_tag: str
    environment: Literal["development", "staging", "production"]
    actor: str


class DeployResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    status: str
    compliance_score_at_deploy: int | None
    temporal_workflow_id: str | None
    started_at: datetime


class ComplianceCheckResult(BaseModel):
    check_name: str
    passed: bool
    score: int
    max_score: int
    detail: str | None = None
    fix_url: str | None = None


class DeployEvaluationResponse(BaseModel):
    service_id: uuid.UUID
    total_score: int
    passing_threshold: int = 80
    allowed: bool
    checks: list[ComplianceCheckResult]
    blocked_reason: str | None = None


# ── Error Budget ─────────────────────────────────────────────

BurnRateStatus = Literal["critical", "fast_burn", "slow_burn", "watch", "healthy"]


class ErrorBudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service_id: uuid.UUID
    budget_consumed_pct: float
    budget_remaining_pct: float
    burn_rate_1h: float
    burn_rate_6h: float
    burn_rate_72h: float
    status: BurnRateStatus
    deploy_frozen: bool
    window_start: datetime
    window_end: datetime


# ── Auth ─────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Health ───────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: dict[str, str]
