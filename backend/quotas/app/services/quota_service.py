from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import QuotaConsumption, TeamQuota
from app.core.logging import get_logger

logger = get_logger(__name__)

async def get_team_utilisation(db: AsyncSession, team_id: str) -> dict:
    quota = (await db.execute(select(TeamQuota).where(TeamQuota.team_id == team_id))).scalar_one_or_none()
    if not quota:
        return {}

    agg = (await db.execute(
        select(
            func.sum(QuotaConsumption.cpu_cores_used).label("cpu"),
            func.sum(QuotaConsumption.memory_gb_used).label("mem"),
            func.sum(QuotaConsumption.storage_gb_used).label("storage"),
            func.sum(QuotaConsumption.cost_usd_current_month).label("cost"),
        ).where(QuotaConsumption.team_id == team_id)
    )).one()

    cpu_used = agg.cpu or 0.0
    mem_used = agg.mem or 0.0
    storage_used = agg.storage or 0.0
    cost_used = agg.cost or 0.0

    over_dimensions = []
    if cpu_used > quota.cpu_cores_limit:
        over_dimensions.append("cpu")
    if mem_used > quota.memory_gb_limit:
        over_dimensions.append("memory")
    if storage_used > quota.storage_gb_limit:
        over_dimensions.append("storage")
    if cost_used > quota.monthly_cost_limit_usd:
        over_dimensions.append("cost")

    return {
        "team_id": team_id,
        "limits": {"cpu_cores": quota.cpu_cores_limit, "memory_gb": quota.memory_gb_limit,
                   "storage_gb": quota.storage_gb_limit, "cost_usd": quota.monthly_cost_limit_usd},
        "consumed": {"cpu_cores": cpu_used, "memory_gb": mem_used,
                     "storage_gb": storage_used, "cost_usd": cost_used},
        "utilisation_pct": {
            "cpu": round(cpu_used / quota.cpu_cores_limit * 100, 1) if quota.cpu_cores_limit > 0 else 0,
            "memory": round(mem_used / quota.memory_gb_limit * 100, 1) if quota.memory_gb_limit > 0 else 0,
            "storage": round(storage_used / quota.storage_gb_limit * 100, 1) if quota.storage_gb_limit > 0 else 0,
            "cost": round(cost_used / quota.monthly_cost_limit_usd * 100, 1) if quota.monthly_cost_limit_usd > 0 else 0,
        },
        "over_quota": len(over_dimensions) > 0,
        "over_quota_dimensions": over_dimensions,
    }
