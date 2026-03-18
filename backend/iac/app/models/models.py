import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class IaCPlan(Base):
    __tablename__ = "iac_plans"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    team_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tool: Mapped[str] = mapped_column(String(20), nullable=False)  # terraform | pulumi
    module_path: Mapped[str] = mapped_column(String(500), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    variables: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    diff_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_cost_delta_usd: Mapped[float] = mapped_column(Float, default=0.0)
    resources_to_add: Mapped[int] = mapped_column(Integer, default=0)
    resources_to_change: Mapped[int] = mapped_column(Integer, default=0)
    resources_to_destroy: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending|approved|rejected|applied|failed
    approved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    temporal_workflow_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_resources: Mapped[list | None] = mapped_column(JSONB, nullable=True)
