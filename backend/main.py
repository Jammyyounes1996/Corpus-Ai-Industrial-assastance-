from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text
from backend.api.routes.search import router as search_router
from backend.api.routes.files import router as files_router
from backend.api.routes.ingest import router as ingest_router
from backend.api.routes.chat import configure_chat_cors, router as chat_router
from backend.api.routes.models import router as models_router
from backend.api.routes.evaluation import router as evaluation_router
from backend.config.settings import get_settings
from backend.database.database import Base, configure_sqlite_pragmas, engine
from backend.schemas.health import HealthResponse
from backend.utils.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    configure_logging()
    logger.info("Starting {}", get_settings().APP_NAME)

    settings = get_settings()
    await configure_sqlite_pragmas()

    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created (DEBUG mode — use Alembic in production)")
    else:
        logger.info("Database migrations managed by Alembic")

    from backend.core.retrieval.qdrant_client import qdrant_retriever
    try:
        qdrant_retriever.ensure_collection()
        logger.info("Qdrant collection verified")
    except Exception as exc:
        logger.warning("Qdrant collection verification failed: {}", exc)

    yield

    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Industrial AI Assistant",
    version="1.0.0",
    description="AI-powered assistant for industrial environments",
    lifespan=lifespan,
)

configure_chat_cors(app)


app.include_router(search_router)
app.include_router(files_router)
app.include_router(ingest_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(evaluation_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions with a structured response."""
    logger.exception("Unhandled exception: {} - {}", type(exc).__name__, str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "message": str(exc),
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health status of the backend and its dependencies.

    Always returns HTTP 200 with appropriate status field:
    - "ok": All services operational
    - "degraded": Some services unavailable
    """
    settings = get_settings()

    database_status = "disconnected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception as exc:
        logger.warning("Database health check failed: {}", exc)
        database_status = "disconnected"

    qdrant_status = "disconnected"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.QDRANT_URL}/collections", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                collections = {c.get("name", "") for c in data.get("result", {}).get("collections", [])}
                if settings.QDRANT_COLLECTION in collections:
                    qdrant_status = "connected"
                else:
                    qdrant_status = "collection_missing"
                    logger.warning("Qdrant connected but collection '{}' not found", settings.QDRANT_COLLECTION)
    except Exception as exc:
        logger.warning("Qdrant health check failed: {}", exc)

    ollama_status = "disconnected"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            if response.status_code == 200:
                ollama_status = "connected"
    except Exception as exc:
        logger.warning("Ollama health check failed: {}", exc)

    # Determine overall status based on service health
    if (
        database_status == "connected"
        and qdrant_status == "connected"
        and ollama_status == "connected"
    ):
        overall_status = "ok"
    else:
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        database=database_status,
        qdrant=qdrant_status,
        ollama=ollama_status,
    )
