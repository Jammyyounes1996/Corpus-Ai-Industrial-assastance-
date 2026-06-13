from __future__ import annotations

import base64
import io
from pathlib import Path

from loguru import logger
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.database import crud


class PdfOcrProcessor:
    """Renders PDF pages as images using PyMuPDF and OCRs each page via Ollama vision."""

    OCR_SYSTEM_PROMPT = (
        "You are an expert OCR assistant for industrial documents. "
        "Extract ALL text from this image exactly as it appears. "
        "Preserve layout, tables, and formatting. "
        "If the image contains no text, respond with: [NO TEXT DETECTED]"
    )

    def __init__(self) -> None:
        self._settings = get_settings()

    def _render_pages(self, pdf_path: str) -> list[bytes]:
        """Render each PDF page to PNG bytes using PyMuPDF."""
        import fitz

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        max_pages = self._settings.OCR_PDF_MAX_PAGES
        pages_to_render = min(total_pages, max_pages)

        rendered: list[bytes] = []
        try:
            for page_idx in range(pages_to_render):
                try:
                    page = doc[page_idx]
                    zoom = 2.0
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG", optimize=True)
                    rendered.append(buf.getvalue())
                except Exception:
                    logger.exception(
                        "Failed to render page {}/{} for pdf_path={}",
                        page_idx + 1, total_pages, pdf_path,
                    )
                    raise
        finally:
            doc.close()

        if len(rendered) < total_pages:
            logger.warning(
                "PDF has {} pages but OCR limit is {} — only first {} processed",
                total_pages, max_pages, len(rendered),
            )

        return rendered

    async def _ocr_page(self, image_bytes: bytes, page_num: int) -> str:
        """OCR a single page image via Ollama vision model."""
        import httpx

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "model": self._settings.OCR_MODEL_NAME,
            "prompt": f"Extract all text from page {page_num + 1} of this document.",
            "images": [b64_image],
            "stream": False,
            "system": self.OCR_SYSTEM_PROMPT,
            "options": {"temperature": 0.1, "num_predict": 4096},
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._settings.OLLAMA_BASE_URL}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    async def extract_text(
        self,
        session: AsyncSession,
        *,
        file_id: str,
        pdf_path: str,
    ) -> dict:
        """Full PDF OCR pipeline: render pages, OCR each, cache result.

        Args:
            session: Database session.
            file_id: Existing File record ID.
            pdf_path: Path to the PDF on disk.

        Returns:
            Dict with file_id, extracted_text, pages_processed, model_used, cached.
        """
        model_used = self._settings.OCR_MODEL_NAME

        existing = await crud.get_ocr_result_by_file_id(session, file_id)
        if existing and existing.model_used == model_used:
            logger.info("PDF OCR cache hit for file_id={}", file_id)
            return {
                "file_id": file_id,
                "extracted_text": existing.extracted_text,
                "pages_processed": existing.extracted_text.count("\n--- PAGE"),
                "model_used": model_used,
                "cached": True,
            }

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        pages = self._render_pages(str(path))
        if not pages:
            raise ValueError("No pages could be rendered from the PDF")

        page_texts: list[str] = []
        for idx, page_bytes in enumerate(pages):
            logger.info("OCR page {}/{} for file_id={}", idx + 1, len(pages), file_id)
            text = await self._ocr_page(page_bytes, idx)
            page_texts.append(f"--- PAGE {idx + 1} ---\n{text}")

        full_text = "\n\n".join(page_texts)

        if existing:
            existing.extracted_text = full_text
            existing.model_used = model_used
            await session.flush()
        else:
            await crud.create_ocr_result(
                session,
                file_id=file_id,
                extracted_text=full_text,
                model_used=model_used,
            )

        logger.info(
            "PDF OCR complete: file_id={}, {} pages, {} chars",
            file_id, len(pages), len(full_text),
        )

        return {
            "file_id": file_id,
            "extracted_text": full_text,
            "pages_processed": len(pages),
            "model_used": model_used,
            "cached": False,
        }


pdf_ocr_processor = PdfOcrProcessor()
