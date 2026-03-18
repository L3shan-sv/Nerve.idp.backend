import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

async def generate_plan(service_id: str, tool: str, module_path: str, variables: dict) -> dict:
    """
    Generate a Terraform/Pulumi plan.
    Phase 2: connect to Terraform Cloud API / Pulumi Automation API.
    Currently returns a realistic mock plan for development.
    """
    logger.info("generating IaC plan", service_id=service_id, tool=tool)
    return {
        "diff_summary": f"+ 2 to add, ~ 1 to change, 0 to destroy in {module_path}",
        "estimated_cost_delta_usd": 14.50,
        "resources_to_add": 2,
        "resources_to_change": 1,
        "resources_to_destroy": 0,
    }

async def apply_plan(plan_id: str, tool: str, module_path: str, variables: dict) -> list[str]:
    """
    Apply an approved IaC plan.
    Phase 2: real Terraform Cloud apply run / pulumi up.
    """
    logger.info("applying IaC plan", plan_id=plan_id, tool=tool)
    return [
        f"aws_rds_instance.{plan_id[:8]}_db",
        f"aws_elasticache_cluster.{plan_id[:8]}_cache",
    ]
