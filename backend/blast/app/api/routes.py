from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import DependencyEdge
from app.schemas.schemas import BlastRadiusResponse, DependencyCreate
from app.services.neo4j_service import get_blast_radius, upsert_service_node

router = APIRouter()

@router.get("/blast/{service_id}", response_model=BlastRadiusResponse, tags=["blast"])
async def blast_radius(
    service_id: str,
    depth: int = Query(3, ge=1, le=5),
    _: dict = Depends(get_current_user),
) -> BlastRadiusResponse:
    result = await get_blast_radius(service_id, depth)
    return BlastRadiusResponse(**result)

@router.post("/blast/dependency", tags=["blast"])
async def add_dependency(
    payload: DependencyCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    edge = DependencyEdge(
        source_service_id=payload.source_service_id,
        target_service_id=payload.target_service_id,
        protocol=payload.protocol,
        weight=payload.weight,
        critical=payload.critical,
    )
    db.add(edge)
    await db.flush()
    # also upsert into Neo4j
    await upsert_service_node(payload.source_service_id, payload.source_service_id, "unknown")
    await upsert_service_node(payload.target_service_id, payload.target_service_id, "unknown")
    return {"created": True, "source": payload.source_service_id, "target": payload.target_service_id}
