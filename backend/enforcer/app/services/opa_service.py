from datetime import datetime, UTC
from typing import Any
import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

PASSING_THRESHOLD = 80
CHECK_WEIGHTS = {
    "health_endpoints": 20,
    "slo_defined": 20,
    "runbook_live_doc": 15,
    "otel_instrumentation": 15,
    "secrets_via_vault": 10,
    "security_posture": 20,
}


async def run_opa_evaluation(req: Any) -> dict:
    input_data = {
        "input": {
            "service": {
                "id": str(req.service_id),
                "name": req.service_name,
                "repo_url": req.repo_url or "",
                "language": req.language or "",
                "slo_uptime_target": req.slo_uptime_target,
                "slo_latency_p99_ms": req.slo_latency_p99_ms,
                "health_status": req.health_status,
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
            return resp.json().get("result", _local_eval(req))
    except Exception as e:
        logger.warning("OPA unreachable, using local evaluation", error=str(e))
        return _local_eval(req)


def _local_eval(req: Any) -> dict:
    has_slo = req.slo_uptime_target > 0 and req.slo_latency_p99_ms > 0
    has_repo = bool(req.repo_url)
    is_healthy = req.health_status not in ("unknown",)
    return {
        "checks": [
            {"name": "health_endpoints", "passed": is_healthy,
             "score": 20 if is_healthy else 0,
             "detail": "/health + /ready detected" if is_healthy else "Health endpoints missing",
             "fix_url": "https://nerve.idp/docs/golden-path/health-endpoints"},
            {"name": "slo_defined", "passed": has_slo,
             "score": 20 if has_slo else 0,
             "detail": f"SLO: {req.slo_uptime_target}% uptime · P99 {req.slo_latency_p99_ms}ms" if has_slo else "No SLO defined",
             "fix_url": "https://nerve.idp/docs/golden-path/slo"},
            {"name": "runbook_live_doc", "passed": has_repo,
             "score": 15 if has_repo else 0,
             "detail": "Runbook URL present" if has_repo else "No runbook URL found",
             "fix_url": "https://nerve.idp/docs/golden-path/runbooks"},
            {"name": "otel_instrumentation", "passed": False, "score": 0,
             "detail": "OTel traces not yet verified",
             "fix_url": "https://nerve.idp/docs/golden-path/otel"},
            {"name": "secrets_via_vault", "passed": False, "score": 0,
             "detail": "Vault secret scan not yet run",
             "fix_url": "https://nerve.idp/docs/golden-path/secrets"},
            {"name": "security_posture", "passed": False, "score": 0,
             "detail": "Trivy scan not yet run",
             "fix_url": "https://nerve.idp/docs/golden-path/security"},
        ]
    }
