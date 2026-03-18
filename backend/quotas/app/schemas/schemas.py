import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class QuotaCreate(BaseModel):
    team_id: str
    cpu_cores_limit: float = Field(default=10.0, gt=0)
    memory_gb_limit: float = Field(default=20.0, gt=0)
    storage_gb_limit: float = Field(default=100.0, gt=0)
    monthly_cost_limit_usd: float = Field(default=1000.0, gt=0)

class QuotaUpdate(BaseModel):
    cpu_cores_limit: float | None = None
    memory_gb_limit: float | None = None
    storage_gb_limit: float | None = None
    monthly_cost_limit_usd: float | None = None

class ConsumptionUpdate(BaseModel):
    service_id: str
    cpu_cores_used: float = 0.0
    memory_gb_used: float = 0.0
    storage_gb_used: float = 0.0
    cost_usd_current_month: float = 0.0

class QuotaStatusResponse(BaseModel):
    team_id: str
    limits: dict
    consumed: dict
    utilisation_pct: dict
    over_quota: bool
    over_quota_dimensions: list[str]
