import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def query_prometheus(query: str) -> float | None:
    """Run an instant PromQL query, return the first scalar value."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.prometheus_url}/api/v1/query",
                params={"query": query},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if results:
                return float(results[0]["value"][1])
            return None
    except Exception as e:
        logger.warning("prometheus query failed", query=query, error=str(e))
        return None


async def get_error_rate(service_name: str, window: str = "1h") -> float:
    """Return error rate (0-1) for a service over the given window."""
    query = (
        f'sum(rate(http_requests_total{{service="{service_name}",status=~"5.."}}[{window}])) '
        f'/ sum(rate(http_requests_total{{service="{service_name}"}}[{window}]))'
    )
    result = await query_prometheus(query)
    return result if result is not None else 0.0


async def get_burn_rate(service_name: str, slo_target: float, window: str = "1h") -> float:
    """
    Calculate multi-window burn rate using Google SRE model.
    burn_rate = error_rate / (1 - slo_target/100) / (window_hours / (30*24))
    """
    error_rate = await get_error_rate(service_name, window)
    error_budget_rate = 1.0 - (slo_target / 100.0)
    if error_budget_rate <= 0:
        return 0.0

    window_hours = {"1h": 1, "6h": 6, "72h": 72}.get(window, 1)
    window_fraction = window_hours / (30 * 24)

    return (error_rate / error_budget_rate) / window_fraction if window_fraction > 0 else 0.0


def classify_alert_status(burn_1h: float, burn_6h: float, burn_72h: float) -> str:
    """Google SRE multi-window burn rate alert classification."""
    if burn_1h >= 14 and burn_6h >= 14:
        return "critical"
    if burn_1h >= 6 and burn_6h >= 6:
        return "fast_burn"
    if burn_72h >= 3:
        return "slow_burn"
    if burn_72h >= 1:
        return "watch"
    return "healthy"
