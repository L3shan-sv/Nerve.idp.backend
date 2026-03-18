import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Pipeline(Base):
    __tablename__ = "pipelines"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    repo_full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    workflow_name: Mapped[str] = mapped_column(String(200), nullable=False)
    run_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    branch: Mapped[str] = mapped_column(String(200), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)   # queued|in_progress|completed
    conclusion: Mapped[str | None] = mapped_column(String(50), nullable=True)  # success|failure|cancelled
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    html_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
