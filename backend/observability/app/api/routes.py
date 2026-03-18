import uuid
from datetime import datetime, UTC, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import CostRecord, DORASnapshot, ErrorBudget
from app.schemas.schemas import CostResponse, DORAResponse, ErrorBudgetResponse
from app.services.prometheus_service import classify_burn_rate, get_burn_rate, rate_dora

router = APIRouter()

@router.get("/dora/{team_id}", response_model=DORAResponse, tags=["observability"])
async def get_dora(
    team_id: str,
    window: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> DORASnapshot:
    result = await db.execute(
        select(DORASnapshot)
        .where(DORASnapshot.team_id == team_id, DORASnapshot.window_days == window)
        .order_by(DORASnapshot.computed_at.desc())
    )
    snapshot = result.scalar_one_or_none()
    if snapshot:
        return snapshot
    # seed realistic mock data — Phase 2 will compute from real deploys + incidents
    snapshot = DORASnapshot(
        team_id=team_id,
        window_days=window,
        deploy_frequency_per_day=2.4,
        lead_time_hours=3.2,
        mttr_minutes=48.0,
        change_failure_rate_pct=4.1,
        deploy_frequency_rating=rate_dora("deploy_frequency", 2.4),
        lead_time_rating=rate_dora("lead_time_hours", 3.2),
        mttr_rating=rate_dora("mttr_minutes", 48.0),
        cfr_rating=rate_dora("cfr_pct", 4.1),
    )
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)
    return snapshot

@router.get("/error-budget/{service_id}", response_model=ErrorBudgetResponse, tags=["observability"])
async def get_error_budget(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(ErrorBudget)
        .where(ErrorBudget.service_id == service_id)
        .order_by(ErrorBudget.window_start.desc())
    )
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="No error budget found for this service")

    remaining_pct = max(0.0, 100.0 - (budget.consumed_minutes / budget.budget_minutes * 100)) if budget.budget_minutes > 0 else 0.0
    alert_status = classify_burn_rate(budget.burn_rate_1h, budget.burn_rate_6h)

    return ErrorBudgetResponse(
        id=budget.id,
        service_id=budget.service_id,
        slo_target_pct=budget.slo_target_pct,
        budget_minutes=budget.budget_minutes,
        consumed_minutes=budget.consumed_minutes,
        remaining_pct=remaining_pct,
        burn_rate_1h=budget.burn_rate_1h,
        burn_rate_6h=budget.burn_rate_6h,
        burn_rate_72h=budget.burn_rate_72h,
        frozen=budget.frozen,
        alert_status=alert_status,
        window_start=budget.window_start,
        window_end=budget.window_end,
    )

@router.post("/error-budget/{service_id}/seed", tags=["observability"])
async def seed_error_budget(
    service_id: str,
    slo_target: float = Query(99.9, ge=90.0, le=100.0),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    """Create/reset the 30-day error budget window for a service."""
    now = datetime.now(UTC)
    window_start = now - timedelta(days=30)
    budget_minutes = (1.0 - slo_target / 100.0) * 30 * 24 * 60
    budget = ErrorBudget(
        service_id=service_id,
        slo_target_pct=slo_target,
        window_start=window_start,
        window_end=now + timedelta(days=30),
        budget_minutes=budget_minutes,
        consumed_minutes=0.0,
        burn_rate_1h=0.0,
        burn_rate_6h=0.0,
        burn_rate_72h=0.0,
    )
    db.add(budget)
    await db.flush()
    return {"created": True, "budget_minutes": budget_minutes, "service_id": service_id}

@router.get("/cost/{service_id}", response_model=list[CostResponse], tags=["observability"])
async def get_cost(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[CostRecord]:
    result = await db.execute(
        select(CostRecord).where(CostRecord.service_id == service_id).order_by(CostRecord.period_start.desc()).limit(12)
    )
    return list(result.scalars().all())
