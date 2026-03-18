import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

async def query_prometheus(promql: str) -> dict:
    """Run an instant PromQL query."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.prometheus_url}/api/v1/query",
                params={"query": promql},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Prometheus query failed", query=promql, error=str(e))
        return {"status": "error", "data": {"resultType": "vector", "result": []}}

async def get_error_rate(service_id: str, window: str = "1h") -> float:
    """Get the current error rate for a service over the given window."""
    promql = f'rate(http_requests_total{{service="{service_id}",status=~"5.."}}[{window}]) / rate(http_requests_total{{service="{service_id}"}}[{window}])'
    result = await query_prometheus(promql)
    results = result.get("data", {}).get("result", [])
    if results:
        return float(results[0]["value"][1])
    return 0.0

async def get_burn_rate(service_id: str, slo_target: float, window: str = "1h") -> float:
    """
    Calculate multi-window burn rate.
    Burn rate = (actual error rate) / (1 - SLO target)
    """
    error_rate = await get_error_rate(service_id, window)
    error_budget_rate = 1.0 - (slo_target / 100.0)
    if error_budget_rate <= 0:
        return 0.0
    return error_rate / error_budget_rate

def classify_burn_rate(burn_rate_1h: float, burn_rate_6h: float) -> str:
    """
    Google SRE multi-window burn rate classification.
    Returns alert status: critical | fast_burn | slow_burn | watch | healthy
    """
    if burn_rate_1h >= 14 and burn_rate_6h >= 14:
        return "critical"
    if burn_rate_1h >= 6 and burn_rate_6h >= 6:
        return "fast_burn"
    if burn_rate_1h >= 3:
        return "slow_burn"
    if burn_rate_1h >= 1:
        return "watch"
    return "healthy"

def rate_dora(metric: str, value: float) -> str:
    thresholds = {
        "deploy_frequency": [(1.0, "elite"), (0.14, "high"), (0.033, "medium")],
        "lead_time_hours":  [(1.0, "elite"), (24.0, "high"), (168.0, "medium")],
        "mttr_minutes":     [(60.0, "elite"), (1440.0, "high"), (10080.0, "medium")],
        "cfr_pct":          [(5.0, "elite"), (10.0, "high"), (15.0, "medium")],
    }
    for threshold, rating in thresholds.get(metric, []):
        if metric in ("deploy_frequency",):
            if value >= threshold:
                return rating
        else:
            if value <= threshold:
                return rating
    return "low"
