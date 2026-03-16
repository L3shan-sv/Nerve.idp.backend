"""
Claude API client for the AI ops co-pilot.
Wraps anthropic SDK with structured SRE system prompt,
conversation history management, and graceful mock fallback.
"""
from typing import Any
import anthropic
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are the nerve.idp AI ops co-pilot — an embedded SRE expert inside an Internal Developer Platform.

Your role:
- Triage active incidents by correlating error budgets, deploy history, and blast radius
- Suggest concrete remediation steps (rollback, scale, alert routing, dependency isolation)
- Match current incidents to similar past incidents by symptom pattern
- Generate draft post-mortems from incident timelines
- Explain compliance failures and guide engineers to fix them

Response rules:
- Be direct. Engineers are under pressure — no filler.
- Lead with the most likely root cause, then actions.
- Numbered lists for action steps.
- Under 400 words unless the engineer asks for more detail.
- Reference service names, error budget percentages, and burn rates when provided in context."""


async def chat(
    message: str,
    history: list[dict],
    context: dict[str, Any],
) -> str:
    """
    Call Claude API with incident context + conversation history.
    Falls back to structured mock when API key not configured.
    """
    if not settings.anthropic_api_key:
        return _mock_response(message, context)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    context_block = _build_context_block(context)
    messages = [
        *history,
        {"role": "user", "content": f"{context_block}\n\n{message}"},
    ]

    try:
        resp = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return resp.content[0].text
    except anthropic.AuthenticationError:
        logger.error("invalid anthropic API key")
        return _mock_response(message, context)
    except Exception as e:
        logger.warning("claude API call failed", error=str(e))
        return _mock_response(message, context)


def _build_context_block(ctx: dict) -> str:
    if not ctx:
        return ""
    lines = ["[Incident Context]"]
    if ctx.get("service_name"):
        lines.append(f"Service: {ctx['service_name']}")
    if ctx.get("severity"):
        lines.append(f"Severity: {ctx['severity']}")
    if ctx.get("budget_remaining_pct") is not None:
        lines.append(f"Error budget remaining: {ctx['budget_remaining_pct']}%")
    if ctx.get("burn_rate_1h"):
        lines.append(f"Burn rate (1h): {ctx['burn_rate_1h']}x")
    if ctx.get("last_deploy"):
        lines.append(f"Last deploy: {ctx['last_deploy']}")
    if ctx.get("health_status"):
        lines.append(f"Health: {ctx['health_status']}")
    return "\n".join(lines)


def _mock_response(message: str, ctx: dict) -> str:
    """Deterministic mock — used in dev when Anthropic key not set."""
    service = ctx.get("service_name", "the service")
    m = message.lower()

    if any(w in m for w in ("rollback", "revert", "undo")):
        return (
            f"**Rolling back {service}**\n\n"
            "1. `kubectl rollout undo deployment/{service}` — ETA ~90s\n"
            "2. Watch error rate in Grafana — should drop within 2 min\n"
            "3. Confirm all replicas pass /health before closing incident\n"
            "4. Post update in incident channel\n\n"
            "Estimated MTTR: 4 minutes (based on 3 similar rollback incidents)."
        )
    if any(w in m for w in ("budget", "burn", "freeze", "frozen")):
        br = ctx.get("burn_rate_1h", "14")
        remaining = ctx.get("budget_remaining_pct", "0")
        return (
            f"{service} is burning error budget at **{br}x** the sustainable rate.\n"
            f"Budget remaining: {remaining}% — deploy freeze is active.\n\n"
            "Root cause (94% match to INC-2791): stripe-client v4.2.0 breaking change "
            "introduced in the last deploy. Retry timeout dropped from 30s → 3s.\n\n"
            "Recommended actions:\n"
            "1. Rollback to previous image (v1.8.0) — fastest path to recovery\n"
            "2. Or pin stripe-client to v4.1.1 and redeploy\n"
            "3. Deploy freeze lifts automatically once budget recovers above 5%"
        )
    if any(w in m for w in ("log", "error", "exception", "trace")):
        return (
            f"Recent error logs for **{service}**:\n\n"
            "```\n"
            "14:32:01 ERROR stripe-client: connection timeout (30s)\n"
            "14:32:01 ERROR stripe-client: retry 1/3 failed\n"
            "14:32:04 ERROR stripe-client: retry 2/3 failed\n"
            "14:32:07 ERROR stripe-client: max retries exceeded\n"
            "14:32:07 ERROR HTTP 503 returned to caller\n"
            "```\n\n"
            "Pattern started at **14:32 UTC** — 4 minutes after deploy v1.9.0. "
            "All errors trace to stripe-client timeout reduction in v4.2.0."
        )
    if any(w in m for w in ("postmortem", "post-mortem", "post mortem")):
        return (
            f"**Draft post-mortem for {service} — INC-2841**\n\n"
            "**Summary**: Payment service error budget exhausted due to stripe-client v4.2.0 "
            "reducing default timeout from 30s to 3s, causing cascade of 503s.\n\n"
            "**Timeline**:\n"
            "- 14:28 — v1.9.0 deployed (bumped stripe-client 4.1.1 → 4.2.0)\n"
            "- 14:32 — error rate spike detected (14x burn rate)\n"
            "- 14:35 — PagerDuty page fired, on-call engaged\n"
            "- 14:39 — rollback to v1.8.0 initiated\n"
            "- 14:43 — error rate normalised, incident resolved\n\n"
            "**Action items**:\n"
            "1. Pin stripe-client version in requirements.txt\n"
            "2. Add timeout regression test to CI pipeline\n"
            "3. Update dependency bump policy to require explicit changelog review"
        )

    return (
        f"Analysing {service}...\n\n"
        "Based on the current context, the most likely causes are:\n"
        "1. A recent deploy introduced a breaking dependency change\n"
        "2. An upstream service degradation is propagating\n\n"
        "Suggested next steps:\n"
        "1. Type `show logs` to see recent error patterns\n"
        "2. Type `rollback` to revert to the last stable image\n"
        "3. Check the blast radius panel for upstream degradation\n"
        "4. Type `postmortem` to generate a draft incident report"
    )
