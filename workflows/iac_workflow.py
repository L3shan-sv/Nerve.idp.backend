"""
IaCApplyWorkflow — Temporal durable workflow for Terraform/Pulumi operations.

Steps:
  1. Validate IaC request (team quota check)
  2. Generate Terraform/Pulumi plan
  3. Estimate cost delta
  4. *** HUMAN APPROVAL GATE *** — pause and wait for EM sign-off
  5. Apply approved plan
  6. Provision Vault secrets for new resources
  7. Update catalog with new infra bindings
  8. Log to audit trail
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from temporalio import activity, workflow
from temporalio.common import RetryPolicy


IaCTool = Literal["terraform", "pulumi"]


@dataclass
class IaCPlanInput:
    service_id: str
    team_id: str
    tool: IaCTool
    module_path: str
    variables: dict = field(default_factory=dict)
    environment: str = "staging"


@dataclass
class IaCPlanResult:
    plan_id: str
    diff_summary: str
    estimated_cost_delta_usd: float
    resources_to_add: int
    resources_to_change: int
    resources_to_destroy: int


@dataclass
class IaCApplyResult:
    success: bool
    applied_resources: list[str]
    vault_secrets_provisioned: list[str]
    error: str | None = None


retry_policy = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3,
)


# ── Activities ───────────────────────────────────────────────

@activity.defn
async def check_team_quota(team_id: str, estimated_cost: float) -> bool:
    """Verify team has remaining quota budget before applying."""
    # TODO Phase 3: check team_quotas table
    activity.logger.info(f"Checking quota for team {team_id}")
    return True


@activity.defn
async def generate_iac_plan(inp: IaCPlanInput) -> IaCPlanResult:
    """Run terraform plan / pulumi preview, return diff."""
    # TODO Phase 2: Terraform Cloud API / Pulumi Automation API
    activity.logger.info(f"Generating {inp.tool} plan for {inp.service_id}")
    return IaCPlanResult(
        plan_id=f"plan-{inp.service_id[:8]}",
        diff_summary="+ 2 resources to add, ~ 1 to change, 0 to destroy",
        estimated_cost_delta_usd=12.50,
        resources_to_add=2,
        resources_to_change=1,
        resources_to_destroy=0,
    )


@activity.defn
async def apply_iac_plan(plan_id: str, inp: IaCPlanInput) -> list[str]:
    """Apply the approved plan, return list of created resource ARNs."""
    # TODO Phase 2: Terraform Cloud apply / Pulumi up
    activity.logger.info(f"Applying plan {plan_id}")
    return [f"arn:aws:ec2:us-east-1:123456789:instance/i-{plan_id}"]


@activity.defn
async def provision_vault_secrets(service_id: str, resources: list[str]) -> list[str]:
    """Create dynamic Vault secrets for newly provisioned resources."""
    # TODO Phase 2: hvac Vault client
    activity.logger.info(f"Provisioning Vault secrets for {service_id}")
    return [f"secret/nerve/{service_id}/db-credentials"]


@activity.defn
async def update_catalog_bindings(service_id: str, resources: list[str]) -> None:
    """Update service record with new infra resource bindings."""
    # TODO Phase 2: PATCH /api/v1/services/{service_id}
    activity.logger.info(f"Updating catalog bindings for {service_id}")


@activity.defn
async def write_audit_log(service_id: str, actor: str, action: str, outcome: str) -> None:
    """Write immutable audit log entry."""
    # TODO Phase 2: INSERT INTO audit_log
    activity.logger.info(f"Audit: {actor} {action} on {service_id} → {outcome}")


# ── Workflow ─────────────────────────────────────────────────

APPROVAL_SIGNAL = "iac_approved"
REJECTION_SIGNAL = "iac_rejected"


@workflow.defn
class IaCApplyWorkflow:
    def __init__(self) -> None:
        self._approved: bool | None = None

    @workflow.signal
    async def approve(self) -> None:
        self._approved = True

    @workflow.signal
    async def reject(self) -> None:
        self._approved = False

    @workflow.run
    async def run(self, inp: IaCPlanInput, actor: str) -> IaCApplyResult:
        workflow.logger.info(f"IaCApplyWorkflow started for {inp.service_id}")

        try:
            # Step 1 — quota check
            await workflow.execute_activity(
                check_team_quota,
                args=[inp.team_id, 0.0],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )

            # Step 2 — generate plan
            plan = await workflow.execute_activity(
                generate_iac_plan,
                inp,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

            # Step 3 — human approval gate (waits up to 24h)
            # Engineering manager sends approve/reject signal via Nerve portal
            await workflow.wait_condition(
                lambda: self._approved is not None,
                timeout=timedelta(hours=24),
            )

            if not self._approved:
                await workflow.execute_activity(
                    write_audit_log,
                    args=[inp.service_id, actor, "iac_apply", "rejected"],
                    start_to_close_timeout=timedelta(seconds=10),
                )
                return IaCApplyResult(success=False, applied_resources=[], vault_secrets_provisioned=[], error="Plan rejected by approver")

            # Step 4 — apply
            resources = await workflow.execute_activity(
                apply_iac_plan,
                args=[plan.plan_id, inp],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=retry_policy,
            )

            # Step 5 — vault secrets
            secrets = await workflow.execute_activity(
                provision_vault_secrets,
                args=[inp.service_id, resources],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            # Step 6 — update catalog
            await workflow.execute_activity(
                update_catalog_bindings,
                args=[inp.service_id, resources],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )

            # Step 7 — audit
            await workflow.execute_activity(
                write_audit_log,
                args=[inp.service_id, actor, "iac_apply", "success"],
                start_to_close_timeout=timedelta(seconds=10),
            )

            return IaCApplyResult(
                success=True,
                applied_resources=resources,
                vault_secrets_provisioned=secrets,
            )

        except Exception as e:
            workflow.logger.error(f"IaCApplyWorkflow failed: {e}")
            return IaCApplyResult(
                success=False,
                applied_resources=[],
                vault_secrets_provisioned=[],
                error=str(e),
            )
