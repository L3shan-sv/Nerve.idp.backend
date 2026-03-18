import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class TeamQuota(Base):
    __tablename__ = "team_quotas"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    cpu_cores_limit: Mapped[float] = mapped_column(Float, default=10.0)
    memory_gb_limit: Mapped[float] = mapped_column(Float, default=20.0)
    storage_gb_limit: Mapped[float] = mapped_column(Float, default=100.0)
    monthly_cost_limit_usd: Mapped[float] = mapped_column(Float, default=1000.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class QuotaConsumption(Base):
    __tablename__ = "quota_consumption"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_id: Mapped[str] = mapped_column(String(100), nullable=False)
    cpu_cores_used: Mapped[float] = mapped_column(Float, default=0.0)
    memory_gb_used: Mapped[float] = mapped_column(Float, default=0.0)
    storage_gb_used: Mapped[float] = mapped_column(Float, default=0.0)
    cost_usd_current_month: Mapped[float] = mapped_column(Float, default=0.0)
    over_quota: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
