from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import router
from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("docs service starting", port=8009)
    if settings.environment == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("docs tables created/verified")
    logger.info("docs service ready")
    yield
    await engine.dispose()
    logger.info("docs service stopped")


app = FastAPI(
    title="nerve.idp — TechDocs",
    description="TechDocs as code — MkDocs + semantic search",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info("request", method=request.method, path=request.url.path, status=response.status_code)
    return response


app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "docs", "version": "2.0.0"}


@app.get("/ready", tags=["health"])
async def ready():
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "degraded", "db": str(e)})
