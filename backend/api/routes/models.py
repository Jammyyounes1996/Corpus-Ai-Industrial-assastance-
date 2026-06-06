from fastapi import APIRouter, HTTPException
import httpx
from loguru import logger
from backend.config.settings import get_settings

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models")
async def list_models() -> dict:
    """List all Ollama models available locally."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags",
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            models = [
                {
                    "name": m.get("name"),
                    "size_bytes": m.get("size"),
                    "modified_at": m.get("modified_at"),
                    "family": m.get("details", {}).get("family"),
                    "parameter_size": m.get("details", {}).get("parameter_size"),
                }
                for m in data.get("models", [])
            ]
            return {"models": models, "total": len(models)}
    except Exception as exc:
        logger.error("Failed to list Ollama models: {}", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Ollama service: {exc}"
        )
