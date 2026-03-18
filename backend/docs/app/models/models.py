import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class TechDoc(Base):
    __tablename__ = "tech_docs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), default="runbook")  # runbook|architecture|adr|guide
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    repo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    freshness_days: Mapped[int] = mapped_column(Integer, default=0)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    search_vector: Mapped[str | None] = mapped_column(Text, nullable=True)  # tsvector stored as text
    embedding_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # pgvector ref
    last_committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
