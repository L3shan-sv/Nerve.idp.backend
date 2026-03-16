"""
ScaffoldWorkflow — Temporal durable workflow for new service scaffolding.

Steps:
  1. Validate scaffold request (repo name, template, team)
  2. Create GitHub repository from Cookiecutter template
  3. Push golden path CI pipeline (.github/workflows/nerve-ci.yml)
  4. Register service in catalog (POST /api/v1/services)
  5. Create OPA policy entry for new service
  6. Trigger first compliance scan
  7. Send Slack notification to team channel
  8. Return scaffold result with repo URL + catalog ID
"""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy


@dataclass
class ScaffoldInput:
    service_name: str
    team_id: str
    language: str
    template: str = "python-fastapi"
    owner: str = ""
    repo_private: bool = True


@dataclass
class ScaffoldResult:
    service_id: str
    repo_url: str
    catalog_url: str
    compliance_score: int
    success: bool
    error: str | None = None


# ── Activities ───────────────────────────────────────────────

@activity.defn
async def validate_scaffold_request(inp: ScaffoldInput) -> bool:
    """Validate team exists, name is unique, template is available."""
    # TODO Phase 2: real validation against catalog API
    activity.logger.info(f"Validating scaffold request for {inp.service_name}")
    return True


@activity.defn
async def create_github_repo(inp: ScaffoldInput) -> str:
    """Create GitHub repo from Cookiecutter template, return repo URL."""
    # TODO Phase 2: GitHub API + Cookiecutter
    activity.logger.info(f"Creating GitHub repo for {inp.service_name}")
    return f"https://github.com/your-org/{inp.service_name}"


@activity.defn
async def push_ci_pipeline(repo_url: str, language: str) -> bool:
    """Push the golden path CI pipeline to the new repo."""
    # TODO Phase 2: push .github/workflows/nerve-ci.yml
    activity.logger.info(f"Pushing CI pipeline to {repo_url}")
    return True


@activity.defn
async def register_in_catalog(inp: ScaffoldInput, repo_url: str) -> str:
    """Register new service in the Nerve catalog, return service_id."""
    # TODO Phase 2: POST /api/v1/services
    activity.logger.info(f"Registering {inp.service_name} in catalog")
    return "placeholder-service-id"


@activity.defn
async def run_initial_compliance_scan(service_id: str) -> int:
    """Run first OPA compliance evaluation, return score."""
    # TODO Phase 2: POST /api/v1/deploy/{service_id}/evaluate
    activity.logger.info(f"Running initial compliance scan for {service_id}")
    return 40  # new services start low — runbook + OTel + security not yet set up


@activity.defn
async def notify_team(service_name: str, team_id: str, repo_url: str) -> None:
    """Send Slack notification to team channel."""
    # TODO Phase 4: Slack API
    activity.logger.info(f"Notifying team {team_id} about {service_name}")


# ── Workflow ─────────────────────────────────────────────────

retry_policy = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=3,
)


@workflow.defn
class ScaffoldWorkflow:
    @workflow.run
    async def run(self, inp: ScaffoldInput) -> ScaffoldResult:
        workflow.logger.info(f"ScaffoldWorkflow started for {inp.service_name}")

        try:
            # Step 1 — validate
            await workflow.execute_activity(
                validate_scaffold_request,
                inp,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )

            # Step 2 — create GitHub repo
            repo_url = await workflow.execute_activity(
                create_github_repo,
                inp,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            # Step 3 — push CI pipeline
            await workflow.execute_activity(
                push_ci_pipeline,
                args=[repo_url, inp.language],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            # Step 4 — register in catalog
            service_id = await workflow.execute_activity(
                register_in_catalog,
                args=[inp, repo_url],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )

            # Step 5 — initial compliance scan
            score = await workflow.execute_activity(
                run_initial_compliance_scan,
                service_id,
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=retry_policy,
            )

            # Step 6 — notify team
            await workflow.execute_activity(
                notify_team,
                args=[inp.service_name, inp.team_id, repo_url],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )

            return ScaffoldResult(
                service_id=service_id,
                repo_url=repo_url,
                catalog_url=f"https://nerve.idp/catalog/{service_id}",
                compliance_score=score,
                success=True,
            )

        except Exception as e:
            workflow.logger.error(f"ScaffoldWorkflow failed: {e}")
            return ScaffoldResult(
                service_id="",
                repo_url="",
                catalog_url="",
                compliance_score=0,
                success=False,
                error=str(e),
            )
