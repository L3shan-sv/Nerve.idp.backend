import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class DORASnapshot(Base):
    __tablename__ = "dora_snapshots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    deploy_frequency_per_day: Mapped[float] = mapped_column(Float, default=0.0)
    lead_time_hours: Mapped[float] = mapped_column(Float, default=0.0)
    mttr_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    change_failure_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)
    deploy_frequency_rating: Mapped[str] = mapped_column(String(20), default="low")
    lead_time_rating: Mapped[str] = mapped_column(String(20), default="low")
    mttr_rating: Mapped[str] = mapped_column(String(20), default="low")
    cfr_rating: Mapped[str] = mapped_column(String(20), default="low")
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ErrorBudget(Base):
    __tablename__ = "error_budgets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    slo_target_pct: Mapped[float] = mapped_column(Float, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    budget_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    consumed_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    burn_rate_1h: Mapped[float] = mapped_column(Float, default=0.0)
    burn_rate_6h: Mapped[float] = mapped_column(Float, default=0.0)
    burn_rate_72h: Mapped[float] = mapped_column(Float, default=0.0)
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class CostRecord(Base):
    __tablename__ = "cost_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    cost_usd_prev_period: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
