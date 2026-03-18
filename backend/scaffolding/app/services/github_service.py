import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

GOLDEN_PATH_CI = """name: nerve golden path CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          exit-code: 1
          severity: CRITICAL
      - name: Semgrep SAST
        uses: semgrep/semgrep-action@v1
"""

async def create_github_repo(org: str, repo_name: str, private: bool = True) -> str:
    """Create GitHub repo and return its URL. Requires GITHUB_TOKEN in env."""
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"name": repo_name, "private": private, "auto_init": True}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.github.com/orgs/{org}/repos",
                headers=headers, json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("github repo created", repo=data["html_url"])
            return data["html_url"]
    except Exception as e:
        logger.warning("github repo creation failed, using placeholder", error=str(e))
        return f"https://github.com/{org}/{repo_name}"

async def push_ci_pipeline(org: str, repo_name: str) -> bool:
    """Push the nerve golden path CI pipeline to the repo."""
    import base64
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    content = base64.b64encode(GOLDEN_PATH_CI.encode()).decode()
    payload = {
        "message": "chore: add nerve golden path CI pipeline",
        "content": content,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.put(
                f"https://api.github.com/repos/{org}/{repo_name}/contents/.github/workflows/nerve-ci.yml",
                headers=headers, json=payload,
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.warning("CI pipeline push failed", error=str(e))
        return False
