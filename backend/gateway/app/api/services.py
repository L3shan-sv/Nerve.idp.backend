import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Service, Team
from app.schemas.schemas import (
    ServiceCreate,
    ServiceListResponse,
    ServiceResponse,
    ServiceUpdate,
)

router = APIRouter(prefix="/services", tags=["catalog"])


@router.get("", response_model=ServiceListResponse)
async def list_services(
    team: str | None = Query(None),
    health: str | None = Query(None),
    min_score: int | None = Query(None, alias="minScore"),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> ServiceListResponse:
    q = select(Service).options(selectinload(Service.team))

    if team:
        q = q.join(Team).where(Team.slug == team)
    if health:
        q = q.where(Service.health_status == health)
    if min_score is not None:
        q = q.where(Service.compliance_score >= min_score)
    if search:
        q = q.where(Service.name.ilike(f"%{search}%"))

    total_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar_one()

    result = await db.execute(q.offset(skip).limit(limit))
    services = result.scalars().all()

    return ServiceListResponse(total=total, services=list(services))


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Service:
    # verify team exists
    team = await db.get(Team, payload.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    service = Service(**payload.model_dump())
    db.add(service)
    await db.flush()
    await db.refresh(service)
    return service


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Service:
    result = await db.execute(
        select(Service)
        .options(selectinload(Service.team), selectinload(Service.checks))
        .where(Service.id == service_id)
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: uuid.UUID,
    payload: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Service:
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(service, field, value)

    await db.flush()
    await db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> None:
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    await db.delete(service)
