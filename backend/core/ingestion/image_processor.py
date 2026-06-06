from __future__ import annotations

import base64
import uuid
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.core.models.ollama_client import ollama_client
from backend.database import crud


class ImageProcessor:
    """Handles image OCR: save, extract text with the configured vision model, store results."""

    ALLOWED_MIME_TYPES: set[str] = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    OCR_SYSTEM_PROMPT = (
        "You are an expert OCR assistant for industrial documents. "
        "Extract ALL text from this image exactly as it appears. "
        "Preserve layout, tables, and formatting. "
        "If the image contains no text, respond with: [NO TEXT DETECTED]"
    )

    def __init__(self) -> None:
        self._settings = get_settings()
        self._upload_dir = Path("data/uploads")
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def _validate_image(self, content_type: str, size_bytes: int) -> None:
        """Validate image file MIME type and size."""
        if content_type.lower() not in {m.lower() for m in self.ALLOWED_MIME_TYPES}:
            raise ValueError(
                f"Invalid content type: {content_type}. "
                f"Expected one of: {', '.join(sorted(self.ALLOWED_MIME_TYPES))}"
            )
        if size_bytes > self._settings.max_image_size_bytes:
            raise ValueError(
                f"File size ({size_bytes / (1024*1024):.1f} MB) exceeds "
                f"maximum ({self._settings.MAX_IMAGE_SIZE_MB} MB) for image files"
            )

    async def ingest_image(
        self,
        session: AsyncSession,
        *,
        file_content: bytes,
        original_name: str,
        content_type: str,
    ) -> dict:
        """Full image OCR ingestion pipeline.

        1. Validate and save to disk
        2. Extract text using the configured vision model
        3. Store OCR result in DB

        Returns:
            Dict with file_id, filename, status, size_bytes, extracted_text.
        """
        size_bytes = len(file_content)
        self._validate_image(content_type, size_bytes)

        file_uuid = str(uuid.uuid4())
        ext = Path(original_name).suffix or ".jpg"
        disk_path = self._upload_dir / f"{file_uuid}{ext}"

        with open(disk_path, "wb") as f:
            f.write(file_content)
        logger.info("Saved image '{}' to {}", original_name, disk_path)

        db_file = await crud.create_file(
            session,
            original_name=original_name,
            file_type="image",
            disk_path=str(disk_path),
            size_bytes=size_bytes,
        )

        try:
            extracted_text = await self._extract_text(file_content, content_type)
            model_used = self._settings.OLLAMA_MODEL

            await crud.create_ocr_result(
                session,
                file_id=db_file.id,
                extracted_text=extracted_text,
                model_used=model_used,
            )

            await crud.update_file_indexing_status(session, db_file.id, status="indexed")

            logger.info(
                "Image '{}' OCR complete: {} chars extracted",
                original_name,
                len(extracted_text),
            )

            return {
                "file_id": db_file.id,
                "filename": original_name,
                "status": "indexed",
                "size_bytes": size_bytes,
                "extracted_text": extracted_text,
            }

        except Exception as exc:
            logger.error("OCR failed for image '{}': {}", original_name, exc)
            fallback_text = "[OCR FAILED - TEXT UNAVAILABLE]"
            await crud.create_ocr_result(
                session,
                file_id=db_file.id,
                extracted_text=fallback_text,
                model_used="fallback",
            )
            await crud.update_file_indexing_status(session, db_file.id, status="indexed")
            return {
                "file_id": db_file.id,
                "filename": original_name,
                "status": "indexed",
                "size_bytes": size_bytes,
                "extracted_text": fallback_text,
            }

    async def _extract_text(self, image_bytes: bytes, content_type: str) -> str:
        """Extract text from image using the configured vision model.

        Args:
            image_bytes: Raw image file bytes.
            content_type: MIME type of the image.

        Returns:
            Extracted text string.
        """
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self._settings.OLLAMA_MODEL,
            "prompt": "Extract all text from this image.",
            "images": [b64_image],
            "stream": False,
            "system": self.OCR_SYSTEM_PROMPT,
            "options": {"temperature": 0.1, "num_predict": 4096},
        }

        async def _call_ollama() -> str:
            import httpx

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self._settings.OLLAMA_BASE_URL}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()

        return await _call_ollama()


image_processor = ImageProcessor()
