import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
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


class Service(Base):
    __tablename__ = "services"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"), nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_score: Mapped[int] = mapped_column(Integer, default=0)
    maturity_score: Mapped[int] = mapped_column(Integer, default=0)
    slo_uptime_target: Mapped[float] = mapped_column(Float, default=99.9)
    slo_latency_p99_ms: Mapped[int] = mapped_column(Integer, default=500)
    error_budget_consumed_pct: Mapped[float] = mapped_column(Float, default=0.0)
    deploy_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    health_status: Mapped[str] = mapped_column(String(50), default="healthy")
    replica_count: Mapped[int] = mapped_column(Integer, default=1)
    current_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    team: Mapped[Team] = relationship("Team", back_populates="services")
    collection_members: Mapped[list["CollectionMember"]] = relationship("CollectionMember", back_populates="service")


class Collection(Base):
    __tablename__ = "collections"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    filter_tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    members: Mapped[list["CollectionMember"]] = relationship("CollectionMember", back_populates="collection")


class CollectionMember(Base):
    __tablename__ = "collection_members"
    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collections.id"), primary_key=True)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("services.id"), primary_key=True)
    collection: Mapped[Collection] = relationship("Collection", back_populates="members")
    service: Mapped[Service] = relationship("Service", back_populates="collection_members")
