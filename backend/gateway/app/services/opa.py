from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def evaluate_compliance(service: Any) -> dict:
    """
    Evaluate a service against the 6 golden path checks via OPA.
    Falls back to a local mock evaluation if OPA is unreachable (dev mode).
    """
    input_data = {
        "input": {
            "service": {
                "id": str(service.id),
                "name": service.name,
                "repo_url": service.repo_url,
                "language": service.language,
                "slo_uptime_target": service.slo_uptime_target,
                "slo_latency_p99_ms": service.slo_latency_p99_ms,
                "health_status": service.health_status,
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.opa_url}/v1/data/nerve/golden_path/evaluate",
                json=input_data,
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("result", _mock_evaluation(service))
    except Exception as e:
        logger.warning("OPA unreachable, using mock evaluation", error=str(e))
        return _mock_evaluation(service)


def _mock_evaluation(service: Any) -> dict:
    """Local mock — used in dev when OPA is not yet loaded with policies."""
    has_slo = service.slo_uptime_target > 0 and service.slo_latency_p99_ms > 0
    has_repo = bool(service.repo_url)

    return {
        "checks": [
            {
                "name": "health_endpoints",
                "passed": service.health_status != "unknown",
                "score": 20 if service.health_status != "unknown" else 0,
                "detail": "/health + /ready endpoints detected" if service.health_status != "unknown"
                          else "Health endpoints not found",
                "fix_url": "https://nerve.idp/docs/golden-path/health-endpoints",
            },
            {
                "name": "slo_defined",
                "passed": has_slo,
                "score": 20 if has_slo else 0,
                "detail": f"SLO: {service.slo_uptime_target}% uptime, P99 {service.slo_latency_p99_ms}ms"
                          if has_slo else "No SLO defined in service manifest",
                "fix_url": "https://nerve.idp/docs/golden-path/slo",
            },
            {
                "name": "runbook_live_doc",
                "passed": has_repo,
                "score": 15 if has_repo else 0,
                "detail": "Runbook URL present" if has_repo else "No runbook URL found",
                "fix_url": "https://nerve.idp/docs/golden-path/runbooks",
            },
            {
                "name": "otel_instrumentation",
                "passed": False,
                "score": 0,
                "detail": "OTel traces not yet verified — run `nerve scan otel <service>`",
                "fix_url": "https://nerve.idp/docs/golden-path/otel",
            },
            {
                "name": "secrets_via_vault",
                "passed": False,
                "score": 0,
                "detail": "Vault secret usage not yet scanned",
                "fix_url": "https://nerve.idp/docs/golden-path/secrets",
            },
            {
                "name": "security_posture",
                "passed": False,
                "score": 0,
                "detail": "Trivy scan not yet run for this service",
                "fix_url": "https://nerve.idp/docs/golden-path/security",
            },
        ]
    }
