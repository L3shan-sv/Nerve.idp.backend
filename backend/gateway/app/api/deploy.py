import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Deployment, Service
from app.schemas.schemas import (
    ComplianceCheckResult,
    DeployEvaluationResponse,
    DeployRequest,
    DeployResponse,
)
from app.services.opa import evaluate_compliance

router = APIRouter(prefix="/deploy", tags=["deploy"])

PASSING_THRESHOLD = 80

CHECK_WEIGHTS = {
    "health_endpoints": 20,
    "slo_defined": 20,
    "runbook_live_doc": 15,
    "otel_instrumentation": 15,
    "secrets_via_vault": 10,
    "security_posture": 20,
}


@router.get("/{service_id}/evaluate", response_model=DeployEvaluationResponse)
async def evaluate_service(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> DeployEvaluationResponse:
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # call OPA for compliance evaluation
    opa_result = await evaluate_compliance(service)

    checks = [
        ComplianceCheckResult(
            check_name=c["name"],
            passed=c["passed"],
            score=c["score"],
            max_score=CHECK_WEIGHTS.get(c["name"], 0),
            detail=c.get("detail"),
            fix_url=c.get("fix_url"),
        )
        for c in opa_result["checks"]
    ]

    total_score = sum(c.score for c in checks)
    allowed = total_score >= PASSING_THRESHOLD

    # critical CVE = always blocked
    security_check = next((c for c in checks if c.check_name == "security_posture"), None)
    if security_check and security_check.detail and "critical CVE" in security_check.detail:
        allowed = False

    return DeployEvaluationResponse(
        service_id=service_id,
        total_score=total_score,
        allowed=allowed,
        checks=checks,
        blocked_reason=None if allowed else f"Score {total_score}/100 below threshold of {PASSING_THRESHOLD}",
    )


@router.post("", response_model=DeployResponse, status_code=status.HTTP_201_CREATED)
async def submit_deploy(
    payload: DeployRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Deployment:
    service = await db.get(Service, payload.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # check if deploy is frozen (budget exhausted)
    if service.deploy_frozen and payload.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "reason": "budget_exhausted",
                "message": f"Deploys frozen: error budget exhausted for {service.name}",
            },
        )

    # run compliance gate for production
    if payload.environment == "production":
        opa_result = await evaluate_compliance(service)
        total_score = sum(c["score"] for c in opa_result["checks"])

        if total_score < PASSING_THRESHOLD:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "reason": "compliance_failed",
                    "score": total_score,
                    "threshold": PASSING_THRESHOLD,
                    "checks": opa_result["checks"],
                },
            )
    else:
        total_score = service.compliance_score

    deployment = Deployment(
        service_id=payload.service_id,
        actor=payload.actor,
        image_tag=payload.image_tag,
        environment=payload.environment,
        status="pending",
        compliance_score_at_deploy=total_score,
    )
    db.add(deployment)
    await db.flush()
    await db.refresh(deployment)
    return deployment


@router.get("/{deployment_id}/status", response_model=DeployResponse)
async def get_deploy_status(
    deployment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Deployment:
    deployment = await db.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment
