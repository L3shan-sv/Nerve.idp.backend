from typing import Any
import anthropic
import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are the nerve.idp AI ops co-pilot — an expert SRE assistant embedded in an Internal Developer Platform.

Your job is to help engineers triage incidents, understand blast radius, interpret error budgets, and suggest remediation steps.

When responding to incident queries:
1. Identify the likely root cause based on the context provided
2. Give concrete immediate actions (rollback, scale, alert routing)
3. Estimate MTTR based on similar past incidents
4. Cite similar past incidents by ID when relevant
5. Flag if error budget is critical and deploy freeze is warranted

Be direct and precise. Engineers are under pressure. No filler.

Format actions as a numbered list. Keep responses under 400 words unless asked for more detail."""


async def get_copilot_response(
    message: str,
    context: dict[str, Any],
    conversation_history: list[dict],
) -> str:
    """
    Call Anthropic Claude API with incident context and conversation history.
    Falls back to a structured mock response if API key not configured.
    """
    if not settings.anthropic_api_key:
        return _mock_response(message, context)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    context_block = f"""
Current incident context:
- Service: {context.get('service_name', 'unknown')}
- Severity: {context.get('severity', 'unknown')}
- Error budget status: {context.get('budget_status', 'unknown')} ({context.get('budget_remaining_pct', '?')}% remaining)
- Burn rate 1h: {context.get('burn_rate_1h', '?')}x
- Recent deploy: {context.get('last_deploy', 'unknown')}
- Health status: {context.get('health_status', 'unknown')}
"""

    messages = [
        *conversation_history,
        {"role": "user", "content": f"{context_block}\n\nEngineer: {message}"},
    ]

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        logger.warning("anthropic API call failed", error=str(e))
        return _mock_response(message, context)


def _mock_response(message: str, context: dict) -> str:
    service = context.get("service_name", "the service")
    msg_lower = message.lower()

    if "rollback" in msg_lower:
        return (
            f"Rolling back {service} to the previous stable image.\n\n"
            "Immediate steps:\n"
            "1. `kubectl rollout undo deployment/{service}` — estimated 90s\n"
            "2. Monitor error rate in Grafana: should drop within 2 minutes\n"
            "3. Verify /health returns 200 on all replicas\n"
            "4. Update incident channel once rollback is confirmed stable\n\n"
            "Estimated MTTR: 4 minutes based on similar rollback incidents."
        )
    if "budget" in msg_lower or "burn" in msg_lower:
        return (
            f"{service} is burning error budget at {context.get('burn_rate_1h', '14')}x the sustainable rate.\n\n"
            "At this rate the 30-day budget exhausts in ~3 days.\n\n"
            "Recommended actions:\n"
            "1. Review recent deploys — last deploy is the most likely cause\n"
            "2. Check downstream dependencies in the blast radius panel\n"
            "3. If root cause is unclear, rollback to the last known-good image\n"
            "4. Deploy freeze is active — no feature deploys until budget recovers"
        )
    if "log" in msg_lower:
        return (
            f"Recent error logs for {service}:\n\n"
            "```\n"
            "ERROR [payment-service] stripe-client: connection timeout after 30s\n"
            "ERROR [payment-service] stripe-client: retrying (2/3)\n"
            "ERROR [payment-service] stripe-client: max retries exceeded\n"
            "ERROR [payment-service] HTTP 503 returned to upstream\n"
            "```\n\n"
            "Pattern: stripe-client timeouts starting at 14:32 UTC — correlates with deploy v1.9.0 "
            "which bumped stripe-client from v4.1.1 to v4.2.0. Likely breaking change in the client library."
        )

    return (
        f"Based on the current context for {service}:\n\n"
        "Root cause analysis is in progress. To help narrow it down:\n"
        "1. Check the deploy history — was there a recent image push?\n"
        "2. Review the blast radius to see if any upstream dependency degraded\n"
        "3. Pull recent error logs for the service\n\n"
        "Type 'show logs', 'rollback', or 'blast radius' for targeted actions."
    )
