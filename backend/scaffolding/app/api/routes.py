import uuid
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import ScaffoldJob, ScaffoldTemplate
from app.schemas.schemas import ScaffoldJobResponse, ScaffoldRequest, TemplateResponse
from app.services.github_service import create_github_repo, push_ci_pipeline
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

BUILTIN_TEMPLATES = [
    {"name": "python-fastapi", "language": "python", "description": "FastAPI + SQLAlchemy + Alembic + OTel",
     "cookiecutter_url": "https://github.com/nerve-idp/template-python-fastapi"},
    {"name": "go-grpc", "language": "go", "description": "gRPC service + OTel + Prometheus",
     "cookiecutter_url": "https://github.com/nerve-idp/template-go-grpc"},
    {"name": "typescript-express", "language": "typescript", "description": "Express + TypeScript + OTel",
     "cookiecutter_url": "https://github.com/nerve-idp/template-ts-express"},
]

@router.get("/scaffold/templates", response_model=list[TemplateResponse], tags=["scaffold"])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list:
    result = await db.execute(select(ScaffoldTemplate))
    db_templates = result.scalars().all()
    if db_templates:
        return list(db_templates)
    # seed builtin templates on first call
    seeded = []
    for t in BUILTIN_TEMPLATES:
        tmpl = ScaffoldTemplate(**t, default_vars={})
        db.add(tmpl)
        seeded.append(tmpl)
    await db.flush()
    return seeded

@router.post("/scaffold", response_model=ScaffoldJobResponse, status_code=status.HTTP_202_ACCEPTED, tags=["scaffold"])
async def scaffold_service(
    req: ScaffoldRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ScaffoldJob:
    tmpl_result = await db.execute(select(ScaffoldTemplate).where(ScaffoldTemplate.name == req.template))
    template = tmpl_result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{req.template}' not found")

    job = ScaffoldJob(
        template_id=template.id,
        service_name=req.service_name,
        team_id=req.team_id,
        owner=req.owner,
        language=req.language,
        status="running",
        extra_vars=req.extra_vars,
    )
    db.add(job)
    await db.flush()

    # Phase 2: dispatch Temporal ScaffoldWorkflow — for now run inline
    try:
        repo_url = await create_github_repo(
            org=settings.github_org or "nerve-org",
            repo_name=req.service_name,
            private=req.repo_private,
        )
        await push_ci_pipeline(
            org=settings.github_org or "nerve-org",
            repo_name=req.service_name,
        )
        job.repo_url = repo_url
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.compliance_score = 40  # new services start here — OTel/security not yet configured
    except Exception as e:
        job.status = "failed"
        job.error = str(e)

    await db.flush()
    await db.refresh(job)
    return job

@router.get("/scaffold/{job_id}", response_model=ScaffoldJobResponse, tags=["scaffold"])
async def get_scaffold_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> ScaffoldJob:
    job = await db.get(ScaffoldJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scaffold job not found")
    return job
