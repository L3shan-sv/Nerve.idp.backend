import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

GITHUB_API = "https://api.github.com"


async def create_github_repo(name: str, private: bool = True) -> dict:
    """Create a GitHub repository under the configured org."""
    headers = {
        "Authorization": f"token {settings.github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "name": name,
        "private": private,
        "auto_init": True,
        "description": f"nerve.idp scaffolded service: {name}",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GITHUB_API}/orgs/{settings.github_org}/repos",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("github repo created", repo=name, url=data["html_url"])
            return {"repo_url": data["html_url"], "clone_url": data["clone_url"]}
    except Exception as e:
        logger.warning("github repo creation failed — using mock", error=str(e))
        # dev fallback when GitHub token not configured
        return {
            "repo_url": f"https://github.com/{settings.github_org or 'your-org'}/{name}",
            "clone_url": f"https://github.com/{settings.github_org or 'your-org'}/{name}.git",
        }


async def push_nerve_ci_pipeline(repo_url: str, language: str) -> bool:
    """
    Push the nerve golden path CI workflow to the scaffolded repo.
    Phase 2: implement via GitHub Contents API.
    """
    logger.info("pushing CI pipeline", repo=repo_url, language=language)
    # TODO Phase 2: push .github/workflows/nerve-ci.yml via GitHub Contents API
    return True


AVAILABLE_TEMPLATES = [
    {
        "name": "python-fastapi",
        "language": "python",
        "description": "FastAPI + SQLAlchemy + Alembic + OTel + pytest",
        "repo_url": "https://github.com/nerve-idp/template-python-fastapi",
        "variables": {"app_name": "", "port": 8000, "db": True, "redis": False},
    },
    {
        "name": "go-grpc",
        "language": "go",
        "description": "gRPC service + protobuf + OTel + testify",
        "repo_url": "https://github.com/nerve-idp/template-go-grpc",
        "variables": {"app_name": "", "port": 50051},
    },
    {
        "name": "typescript-express",
        "language": "typescript",
        "description": "Express + Prisma + Jest + OTel",
        "repo_url": "https://github.com/nerve-idp/template-typescript-express",
        "variables": {"app_name": "", "port": 3000, "db": True},
    },
    {
        "name": "rust-axum",
        "language": "rust",
        "description": "Axum + SQLx + tokio + OTel",
        "repo_url": "https://github.com/nerve-idp/template-rust-axum",
        "variables": {"app_name": "", "port": 8000},
    },
]
