import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    services: Mapped[list["Service"]] = relationship("Service", back_populates="team")
    quota: Mapped["TeamQuota"] = relationship("TeamQuota", back_populates="team", uselist=False)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"), nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=True)
    repo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Compliance + maturity
    compliance_score: Mapped[int] = mapped_column(Integer, default=0)
    maturity_score: Mapped[int] = mapped_column(Integer, default=0)

    # SLOs
    slo_uptime_target: Mapped[float] = mapped_column(Float, default=99.9)
    slo_latency_p99_ms: Mapped[int] = mapped_column(Integer, default=500)

    # Error budget
    error_budget_consumed_pct: Mapped[float] = mapped_column(Float, default=0.0)
    deploy_frozen: Mapped[bool] = mapped_column(Boolean, default=False)

    # Health
    health_status: Mapped[str] = mapped_column(String(50), default="healthy")
    replica_count: Mapped[int] = mapped_column(Integer, default=1)
    current_version: Mapped[str] = mapped_column(String(100), nullable=True)
    last_deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    team: Mapped[Team] = relationship("Team", back_populates="services")
    deployments: Mapped[list["Deployment"]] = relationship("Deployment", back_populates="service")
    checks: Mapped[list["ServiceCheck"]] = relationship("ServiceCheck", back_populates="service")


class ServiceCheck(Base):
    __tablename__ = "service_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("services.id"), nullable=False)
    check_name: Mapped[str] = mapped_column(String(100), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    service: Mapped[Service] = relationship("Service", back_populates="checks")


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("services.id"), nullable=False)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    image_tag: Mapped[str] = mapped_column(String(500), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    compliance_score_at_deploy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temporal_workflow_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    service: Mapped[Service] = relationship("Service", back_populates="deployments")


class ErrorBudget(Base):
    __tablename__ = "error_budgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("services.id"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    budget_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    consumed_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    burn_rate_1h: Mapped[float] = mapped_column(Float, default=0.0)
    burn_rate_6h: Mapped[float] = mapped_column(Float, default=0.0)
    burn_rate_72h: Mapped[float] = mapped_column(Float, default=0.0)
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)


class TeamQuota(Base):
    __tablename__ = "team_quotas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"), unique=True, nullable=False)
    cpu_cores_limit: Mapped[float] = mapped_column(Float, default=10.0)
    memory_gb_limit: Mapped[float] = mapped_column(Float, default=20.0)
    storage_gb_limit: Mapped[float] = mapped_column(Float, default=100.0)
    monthly_cost_limit_usd: Mapped[float] = mapped_column(Float, default=1000.0)

    team: Mapped[Team] = relationship("Team", back_populates="quota")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
