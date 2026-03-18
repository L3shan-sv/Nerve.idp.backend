from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.services.graph import close_driver

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("blast service starting", port=8007)
    logger.info("blast service ready — Neo4j lazy-connect on first request")
    yield
    await close_driver()
    logger.info("blast service stopped, Neo4j driver closed")


app = FastAPI(
    title="nerve.idp — Blast Radius",
    description="Blast radius visualizer — Neo4j dependency graph",
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
    return {"status": "ok", "service": "blast", "version": "2.0.0"}


@app.get("/ready", tags=["health"])
async def ready():
    # Blast service uses Neo4j — test the connection on ready probe
    try:
        from app.services.graph import get_driver
        async with get_driver().session() as session:
            await session.run("RETURN 1")
        return {"status": "ready", "neo4j": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "degraded", "neo4j": str(e)})
