import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

DoraRating = Literal["elite", "high", "medium", "low"]

class DORAResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    team_id: str
    window_days: int
    deploy_frequency_per_day: float
    lead_time_hours: float
    mttr_minutes: float
    change_failure_rate_pct: float
    deploy_frequency_rating: DoraRating
    lead_time_rating: DoraRating
    mttr_rating: DoraRating
    cfr_rating: DoraRating
    computed_at: datetime

class ErrorBudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    service_id: str
    slo_target_pct: float
    budget_minutes: float
    consumed_minutes: float
    remaining_pct: float = 0.0
    burn_rate_1h: float
    burn_rate_6h: float
    burn_rate_72h: float
    frozen: bool
    alert_status: str = "healthy"
    window_start: datetime
    window_end: datetime

class CostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    service_id: str
    period_start: datetime
    period_end: datetime
    cost_usd: float
    cost_usd_prev_period: float | None
    anomaly_flag: bool
    anomaly_pct: float | None
    breakdown: dict | None
    synced_at: datetime
