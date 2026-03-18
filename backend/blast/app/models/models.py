import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class DependencyEdge(Base):
    __tablename__ = "dependency_edges"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    protocol: Mapped[str] = mapped_column(String(50), default="http")
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    critical: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class BlastRadiusCache(Base):
    __tablename__ = "blast_radius_cache"
    service_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    depth: Mapped[int] = mapped_column(Integer, default=3)
    affected_services: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    nodes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    edges: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="low")
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
