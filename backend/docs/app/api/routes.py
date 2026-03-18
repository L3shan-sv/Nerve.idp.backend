import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import TechDoc
from app.schemas.schemas import DocCreate, DocResponse, DocSearchResult, DocUpdate
from app.services.search_service import compute_freshness, full_text_search

router = APIRouter()

@router.get("/docs/search", response_model=list[DocSearchResult], tags=["docs"])
async def search_docs(
    q: str = Query(..., min_length=2),
    service_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[dict]:
    return await full_text_search(db, q, service_id, limit)

@router.get("/docs/{service_id}", response_model=list[DocResponse], tags=["docs"])
async def list_docs(
    service_id: str,
    doc_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[TechDoc]:
    q = select(TechDoc).where(TechDoc.service_id == service_id).order_by(TechDoc.updated_at.desc())
    if doc_type:
        q = q.where(TechDoc.doc_type == doc_type)
    result = await db.execute(q)
    return list(result.scalars().all())

@router.post("/docs", response_model=DocResponse, status_code=status.HTTP_201_CREATED, tags=["docs"])
async def create_doc(
    payload: DocCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> TechDoc:
    word_count = len(payload.content_md.split())
    doc = TechDoc(**payload.model_dump(), word_count=word_count)
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc

@router.patch("/docs/{doc_id}", response_model=DocResponse, tags=["docs"])
async def update_doc(
    doc_id: uuid.UUID,
    payload: DocUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> TechDoc:
    doc = await db.get(TechDoc, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doc not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    if payload.content_md:
        doc.word_count = len(payload.content_md.split())
        freshness, is_stale = compute_freshness(doc.last_committed_at, payload.content_md)
        doc.freshness_days = freshness
        doc.is_stale = is_stale
    await db.flush()
    await db.refresh(doc)
    return doc
