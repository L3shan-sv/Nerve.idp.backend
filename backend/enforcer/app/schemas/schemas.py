import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CheckResult(BaseModel):
    check_name: str
    passed: bool
    score: int
    max_score: int
    detail: str | None = None
    fix_url: str | None = None


class EvaluationRequest(BaseModel):
    service_id: uuid.UUID
    service_name: str
    repo_url: str | None = None
    language: str | None = None
    slo_uptime_target: float = 99.9
    slo_latency_p99_ms: int = 500
    health_status: str = "healthy"
    image_digest: str | None = None


class EvaluationResponse(BaseModel):
    service_id: uuid.UUID
    total_score: int
    passing_threshold: int = 80
    allowed: bool
    checks: list[CheckResult]
    blocked_reason: str | None = None
    evaluated_at: datetime


class CVEReportCreate(BaseModel):
    service_id: uuid.UUID
    image_digest: str
    cves: list[dict]


class CVEReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    service_id: uuid.UUID
    image_digest: str
    cve_id: str
    severity: str
    cvss_score: float | None
    package: str | None
    fix_version: str | None
    scanned_at: datetime
