from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import QuotaConsumption, TeamQuota
from app.schemas.schemas import ConsumptionUpdate, QuotaCreate, QuotaStatusResponse, QuotaUpdate
from app.services.quota_service import get_team_utilisation

router = APIRouter()

@router.post("/quotas", status_code=status.HTTP_201_CREATED, tags=["quotas"])
async def create_quota(
    payload: QuotaCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    existing = (await db.execute(select(TeamQuota).where(TeamQuota.team_id == payload.team_id))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Quota for team '{payload.team_id}' already exists")
    quota = TeamQuota(**payload.model_dump())
    db.add(quota)
    await db.flush()
    return {"created": True, "team_id": payload.team_id}

@router.get("/quotas/{team_id}", response_model=QuotaStatusResponse, tags=["quotas"])
async def get_quota_status(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    status_data = await get_team_utilisation(db, team_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="No quota defined for this team")
    return QuotaStatusResponse(**status_data)

@router.patch("/quotas/{team_id}", tags=["quotas"])
async def update_quota(
    team_id: str,
    payload: QuotaUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    quota = (await db.execute(select(TeamQuota).where(TeamQuota.team_id == team_id))).scalar_one_or_none()
    if not quota:
        raise HTTPException(status_code=404, detail="Quota not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(quota, field, value)
    await db.flush()
    return {"updated": True, "team_id": team_id}

@router.post("/quotas/{team_id}/consumption", tags=["quotas"])
async def update_consumption(
    team_id: str,
    payload: ConsumptionUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    existing = (await db.execute(
        select(QuotaConsumption)
        .where(QuotaConsumption.team_id == team_id, QuotaConsumption.service_id == payload.service_id)
    )).scalar_one_or_none()
    if existing:
        existing.cpu_cores_used = payload.cpu_cores_used
        existing.memory_gb_used = payload.memory_gb_used
        existing.storage_gb_used = payload.storage_gb_used
        existing.cost_usd_current_month = payload.cost_usd_current_month
    else:
        db.add(QuotaConsumption(team_id=team_id, **payload.model_dump()))
    await db.flush()
    util = await get_team_utilisation(db, team_id)
    return {"updated": True, "over_quota": util.get("over_quota", False)}
