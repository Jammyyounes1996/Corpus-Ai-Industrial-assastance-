from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text

from backend.api.routes.files import router as files_router
from backend.api.routes.ingest import router as ingest_router
from backend.config.settings import get_settings
from backend.database.database import engine, Base
from backend.schemas.health import HealthResponse
from backend.utils.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    configure_logging()
    logger.info("Starting {}", get_settings().APP_NAME)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified")

    yield

    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Industrial AI Assistant",
    version="1.0.0",
    description="AI-powered assistant for industrial environments",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(ingest_router)
app.include_router(files_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions with a structured response."""
    logger.error("Unhandled exception: {} - {}", type(exc).__name__, str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "message": "An internal error occurred",
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health status of the backend and its dependencies.

    Always returns HTTP 200 with appropriate status field:
    - "ok": All services operational
    - "degraded": Some services unavailable or missing required components (e.g., model not downloaded)
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
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Check if gemma4:e4b model is downloaded
                if "gemma4:e4b" in models or "gemma4" in models:
                    ollama_status = "connected"
                else:
                    ollama_status = "model_missing"
                    logger.warning("Ollama connected but gemma4 model not found. Available: {}", models)
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
