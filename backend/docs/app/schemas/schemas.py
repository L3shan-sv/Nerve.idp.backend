import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

class DocCreate(BaseModel):
    service_id: str
    title: str
    slug: str
    content_md: str
    doc_type: Literal["runbook", "architecture", "adr", "guide"] = "runbook"
    owner: str
    repo_path: str | None = None

class DocUpdate(BaseModel):
    title: str | None = None
    content_md: str | None = None
    owner: str | None = None

class DocResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    service_id: str
    title: str
    slug: str
    doc_type: str
    owner: str
    repo_path: str | None
    word_count: int
    freshness_days: int
    is_stale: bool
    last_committed_at: datetime | None
    created_at: datetime
    updated_at: datetime

class DocSearchResult(BaseModel):
    doc_id: uuid.UUID
    service_id: str
    title: str
    slug: str
    doc_type: str
    excerpt: str
    score: float
    is_stale: bool
