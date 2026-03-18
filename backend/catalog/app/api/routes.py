import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Collection, CollectionMember, Service, Team
from app.schemas.schemas import (
    CollectionCreate, CollectionResponse,
    FleetOpRequest, FleetOpResponse,
    ServiceCreate, ServiceListResponse, ServiceResponse, ServiceUpdate,
    TeamCreate, TeamResponse,
)

router = APIRouter()


# ── Teams ────────────────────────────────────────────────────

@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED, tags=["teams"])
async def create_team(
    payload: TeamCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Team:
    existing = await db.execute(select(Team).where(Team.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Team with slug '{payload.slug}' already exists")
    team = Team(**payload.model_dump())
    db.add(team)
    await db.flush()
    await db.refresh(team)
    return team


@router.get("/teams", response_model=list[TeamResponse], tags=["teams"])
async def list_teams(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[Team]:
    result = await db.execute(select(Team).order_by(Team.name))
    return list(result.scalars().all())


# ── Services ─────────────────────────────────────────────────

@router.get("/services", response_model=ServiceListResponse, tags=["catalog"])
async def list_services(
    team: str | None = Query(None),
    health: str | None = Query(None),
    min_score: int | None = Query(None, alias="minScore"),
    frozen: bool | None = Query(None),
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
    if frozen is not None:
        q = q.where(Service.deploy_frozen == frozen)
    if search:
        q = q.where(Service.name.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    services = (await db.execute(q.order_by(Service.name).offset(skip).limit(limit))).scalars().all()
    return ServiceListResponse(total=total, services=list(services))


@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED, tags=["catalog"])
async def create_service(
    payload: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Service:
    team = await db.get(Team, payload.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    existing = await db.execute(select(Service).where(Service.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Service slug '{payload.slug}' already exists")
    service = Service(**payload.model_dump())
    db.add(service)
    await db.flush()
    await db.refresh(service)
    return service


@router.get("/services/{service_id}", response_model=ServiceResponse, tags=["catalog"])
async def get_service(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Service:
    result = await db.execute(
        select(Service).options(selectinload(Service.team)).where(Service.id == service_id)
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.patch("/services/{service_id}", response_model=ServiceResponse, tags=["catalog"])
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


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["catalog"])
async def delete_service(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> None:
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    await db.delete(service)


# ── Collections ──────────────────────────────────────────────

@router.get("/collections", response_model=list[CollectionResponse], tags=["fleet"])
async def list_collections(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[CollectionResponse]:
    result = await db.execute(
        select(Collection).options(selectinload(Collection.members))
    )
    collections = result.scalars().all()
    out = []
    for c in collections:
        out.append(CollectionResponse(
            id=c.id, name=c.name, team_id=c.team_id,
            created_by=c.created_by, created_at=c.created_at,
            member_count=len(c.members),
        ))
    return out


@router.post("/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED, tags=["fleet"])
async def create_collection(
    payload: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CollectionResponse:
    collection = Collection(
        name=payload.name,
        team_id=payload.team_id,
        filter_tags=payload.filter_tags,
        created_by=current_user.get("sub", "unknown"),
    )
    db.add(collection)
    await db.flush()

    for svc_id in payload.service_ids:
        db.add(CollectionMember(collection_id=collection.id, service_id=svc_id))
    await db.flush()

    return CollectionResponse(
        id=collection.id, name=collection.name, team_id=collection.team_id,
        created_by=collection.created_by, created_at=collection.created_at,
        member_count=len(payload.service_ids),
    )


# ── Fleet operations ─────────────────────────────────────────

@router.post("/collections/{collection_id}/ops", response_model=FleetOpResponse, tags=["fleet"])
async def fleet_operation(
    collection_id: uuid.UUID,
    payload: FleetOpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> FleetOpResponse:
    """
    Trigger a bulk operation across all services in a collection.
    Phase 4: real Temporal workflow dispatch. For now returns a planned response.
    """
    collection = await db.get(Collection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    result = await db.execute(
        select(CollectionMember).where(CollectionMember.collection_id == collection_id)
    )
    members = result.scalars().all()
    service_ids = [str(m.service_id) for m in members]

    # Phase 4: dispatch Temporal bulk workflow per service
    # For now: return planned response with placeholder workflow IDs
    workflow_ids = [f"fleet-{payload.operation}-{sid[:8]}" for sid in service_ids]

    return FleetOpResponse(
        operation=payload.operation,
        affected_services=len(service_ids),
        workflow_ids=workflow_ids,
        status="queued",
    )
