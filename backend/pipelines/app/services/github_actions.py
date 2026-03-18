import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

async def fetch_workflow_runs(repo_full_name: str, limit: int = 20) -> list[dict]:
    """Fetch recent GitHub Actions workflow runs for a repo."""
    if not settings.github_token:
        logger.warning("GITHUB_TOKEN not set, returning mock pipeline data")
        return _mock_runs(repo_full_name, limit)
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/actions/runs",
                headers=headers,
                params={"per_page": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("workflow_runs", [])
    except Exception as e:
        logger.warning("GitHub Actions API failed", error=str(e))
        return _mock_runs(repo_full_name, limit)

def _mock_runs(repo: str, limit: int) -> list[dict]:
    from datetime import datetime, timezone
    runs = []
    conclusions = ["success", "success", "failure", "success", "cancelled"]
    for i in range(min(limit, 5)):
        runs.append({
            "id": 9000000 + i,
            "run_number": 100 - i,
            "name": "nerve golden path CI",
            "head_branch": "main",
            "head_sha": f"abc{i:04x}def",
            "actor": {"login": "alice"},
            "status": "completed",
            "conclusion": conclusions[i % len(conclusions)],
            "html_url": f"https://github.com/{repo}/actions/runs/{9000000 + i}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "jobs_url": f"https://api.github.com/repos/{repo}/actions/runs/{9000000 + i}/jobs",
        })
    return runs
