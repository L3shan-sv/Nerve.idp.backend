import uuid
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import CVEReport, ServiceCheck
from app.schemas.schemas import CheckResult, CVEReportCreate, EvaluationRequest, EvaluationResponse
from app.services.opa_service import PASSING_THRESHOLD, run_opa_evaluation

router = APIRouter()


@router.post("/enforce/evaluate", response_model=EvaluationResponse, tags=["enforce"])
async def evaluate(
    req: EvaluationRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> EvaluationResponse:
    result = await run_opa_evaluation(req)
    checks = [
        CheckResult(
            check_name=c["name"], passed=c["passed"],
            score=c["score"], max_score=c.get("max_score", 0),
            detail=c.get("detail"), fix_url=c.get("fix_url"),
        )
        for c in result["checks"]
    ]
    total = sum(c.score for c in checks)
    has_critical = any(
        c.check_name == "security_posture" and c.detail and "CRITICAL" in (c.detail or "")
        for c in checks
    )
    allowed = total >= PASSING_THRESHOLD and not has_critical

    # persist check results
    for c in checks:
        db.add(ServiceCheck(
            service_id=req.service_id,
            check_name=c.check_name,
            passed=c.passed,
            score=c.score,
            max_score=c.max_score,
            detail=c.detail,
            fix_url=c.fix_url,
        ))
    await db.flush()

    return EvaluationResponse(
        service_id=req.service_id,
        total_score=total,
        allowed=allowed,
        checks=checks,
        blocked_reason=None if allowed else (
            "Critical CVE detected" if has_critical
            else f"Score {total}/100 below threshold {PASSING_THRESHOLD}"
        ),
        evaluated_at=datetime.now(UTC),
    )


@router.post("/enforce/cve-report", tags=["security"])
async def ingest_cve_report(
    payload: CVEReportCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    """Ingest Trivy CVE scan results for a service image."""
    inserted = 0
    for cve in payload.cves:
        db.add(CVEReport(
            service_id=payload.service_id,
            image_digest=payload.image_digest,
            cve_id=cve.get("cve_id", "UNKNOWN"),
            severity=cve.get("severity", "UNKNOWN"),
            cvss_score=cve.get("cvss_score"),
            package=cve.get("package"),
            fix_version=cve.get("fix_version"),
        ))
        inserted += 1
    await db.flush()
    return {"ingested": inserted, "service_id": str(payload.service_id)}


@router.get("/enforce/cve-report/{service_id}", tags=["security"])
async def get_cve_report(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(CVEReport)
        .where(CVEReport.service_id == service_id)
        .order_by(CVEReport.scanned_at.desc())
    )
    cves = result.scalars().all()
    by_severity: dict[str, int] = {}
    for cve in cves:
        by_severity[cve.severity] = by_severity.get(cve.severity, 0) + 1
    return {
        "service_id": str(service_id),
        "total": len(cves),
        "by_severity": by_severity,
        "has_critical": by_severity.get("CRITICAL", 0) > 0,
        "cves": [
            {"cve_id": c.cve_id, "severity": c.severity, "package": c.package,
             "fix_version": c.fix_version, "cvss_score": c.cvss_score}
            for c in cves[:50]
        ],
    }
