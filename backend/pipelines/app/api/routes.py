from datetime import datetime, UTC, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Pipeline
from app.schemas.schemas import PipelineListResponse, PipelineResponse, PipelineSyncRequest
from app.services.github_actions import fetch_workflow_runs

router = APIRouter()

@router.get("/pipelines", response_model=PipelineListResponse, tags=["pipelines"])
async def list_pipelines(
    service_id: str | None = Query(None),
    branch: str | None = Query(None),
    conclusion: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> PipelineListResponse:
    q = select(Pipeline).order_by(Pipeline.started_at.desc())
    if service_id:
        q = q.where(Pipeline.service_id == service_id)
    if branch:
        q = q.where(Pipeline.branch == branch)
    if conclusion:
        q = q.where(Pipeline.conclusion == conclusion)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    pipelines = (await db.execute(q.offset(skip).limit(limit))).scalars().all()
    return PipelineListResponse(total=total, pipelines=list(pipelines))

@router.post("/pipelines/sync", tags=["pipelines"])
async def sync_pipelines(
    req: PipelineSyncRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    """Pull latest runs from GitHub Actions and upsert into DB."""
    runs = await fetch_workflow_runs(req.repo_full_name, req.limit)
    upserted = 0
    for run in runs:
        existing = await db.execute(select(Pipeline).where(Pipeline.run_id == run["id"]))
        pipeline = existing.scalar_one_or_none()
        started = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")) if isinstance(run.get("created_at"), str) else datetime.now(UTC)
        if not pipeline:
            pipeline = Pipeline(
                service_id=req.service_id,
                repo_full_name=req.repo_full_name,
                workflow_name=run.get("name", "CI"),
                run_id=run["id"],
                run_number=run.get("run_number", 0),
                branch=run.get("head_branch", "main"),
                commit_sha=run.get("head_sha", "")[:40],
                actor=run.get("actor", {}).get("login", "unknown"),
                status=run.get("status", "completed"),
                conclusion=run.get("conclusion"),
                html_url=run.get("html_url"),
                started_at=started,
            )
            db.add(pipeline)
            upserted += 1
    await db.flush()
    return {"synced": upserted, "service_id": req.service_id}
