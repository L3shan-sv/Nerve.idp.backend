import uuid
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import IaCPlan
from app.schemas.schemas import IaCApprovalRequest, IaCPlanRequest, IaCPlanResponse
from app.services.terraform_service import apply_plan, generate_plan

router = APIRouter()

@router.post("/iac/plan", response_model=IaCPlanResponse, status_code=status.HTTP_202_ACCEPTED, tags=["iac"])
async def create_plan(
    req: IaCPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IaCPlan:
    plan_data = await generate_plan(req.service_id, req.tool, req.module_path, req.variables)
    plan = IaCPlan(
        service_id=req.service_id,
        team_id=req.team_id,
        tool=req.tool,
        module_path=req.module_path,
        environment=req.environment,
        variables=req.variables,
        created_by=current_user.get("sub", "unknown"),
        status="pending_approval",
        **plan_data,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan

@router.post("/iac/plan/{plan_id}/approve", response_model=IaCPlanResponse, tags=["iac"])
async def approve_plan(
    plan_id: uuid.UUID,
    req: IaCApprovalRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> IaCPlan:
    plan = await db.get(IaCPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status not in ("pending_approval",):
        raise HTTPException(status_code=409, detail=f"Plan already in status '{plan.status}'")

    if req.approved:
        plan.status = "approved"
        plan.approved_by = req.approver
        plan.approved_at = datetime.now(UTC)
        # Phase 2: signal Temporal IaCApplyWorkflow here
        applied = await apply_plan(str(plan_id), plan.tool, plan.module_path, plan.variables or {})
        plan.applied_resources = applied
        plan.applied_at = datetime.now(UTC)
        plan.status = "applied"
    else:
        plan.status = "rejected"

    await db.flush()
    await db.refresh(plan)
    return plan

@router.get("/iac/plans", response_model=list[IaCPlanResponse], tags=["iac"])
async def list_plans(
    service_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[IaCPlan]:
    q = select(IaCPlan).order_by(IaCPlan.created_at.desc())
    if service_id:
        q = q.where(IaCPlan.service_id == service_id)
    result = await db.execute(q.limit(100))
    return list(result.scalars().all())

@router.get("/iac/plan/{plan_id}", response_model=IaCPlanResponse, tags=["iac"])
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> IaCPlan:
    plan = await db.get(IaCPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan
