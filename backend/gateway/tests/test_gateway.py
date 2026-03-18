"""
Phase 1 test suite — gateway health, auth, services CRUD, deploy gate.
Run with: pytest tests/ -v
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app

# ── Test DB setup ────────────────────────────────────────────

TEST_DATABASE_URL = "postgresql+asyncpg://nerve:nerve_secret@localhost:5432/nerve_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "secret"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ── Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "secret"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_services_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/services")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_and_list_service(client: AsyncClient, auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # create a team first
    # (in Phase 2 teams will have their own endpoint — direct DB insert for now)
    from app.models.models import Team
    from app.core.database import AsyncSessionLocal
    import uuid

    team_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        team = Team(id=team_id, name="Platform Team", slug="platform-team")
        session.add(team)
        await session.commit()

    # create service
    resp = await client.post(
        "/api/v1/services",
        headers=headers,
        json={
            "name": "payment-service",
            "slug": "payment-service",
            "owner": "alice@example.com",
            "language": "python",
            "repo_url": "https://github.com/org/payment-service",
            "team_id": str(team_id),
            "slo_uptime_target": 99.9,
            "slo_latency_p99_ms": 200,
        },
    )
    assert resp.status_code == 201
    service = resp.json()
    assert service["name"] == "payment-service"
    assert service["compliance_score"] == 0

    # list services
    resp = await client.get("/api/v1/services", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(s["slug"] == "payment-service" for s in data["services"])


@pytest.mark.asyncio
async def test_deploy_blocked_below_threshold(client: AsyncClient, auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # get the service we just created
    resp = await client.get("/api/v1/services?search=payment-service", headers=headers)
    services = resp.json()["services"]
    assert len(services) > 0
    service_id = services[0]["id"]

    # evaluate compliance — new service scores low
    resp = await client.get(f"/api/v1/deploy/{service_id}/evaluate", headers=headers)
    assert resp.status_code == 200
    eval_data = resp.json()
    assert eval_data["total_score"] < 80
    assert eval_data["allowed"] is False

    # production deploy should be blocked
    resp = await client.post(
        "/api/v1/deploy",
        headers=headers,
        json={
            "service_id": service_id,
            "image_tag": "v1.0.0",
            "environment": "production",
            "actor": "alice@example.com",
        },
    )
    assert resp.status_code == 403
