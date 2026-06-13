from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ingestion.pdf_ocr_processor import pdf_ocr_processor
from backend.database import crud
from backend.database.database import get_session
from backend.database.models import File

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/{file_id}/extract")
async def extract_pdf_ocr(
    file_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Extract text from a PDF file using OCR (render pages → vision model).

    Supports caching: if OCR was already done with the same model, returns cached result.
    """
    db_file = await session.get(File, file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail={"error": "NotFound", "message": f"File {file_id} not found"})

    if db_file.file_type != "pdf":
        raise HTTPException(
            status_code=400,
            detail={"error": "InvalidFileType", "message": f"OCR extraction is only supported for PDF files, got '{db_file.file_type}'"},
        )

    try:
        result = await pdf_ocr_processor.extract_text(
            session,
            file_id=file_id,
            pdf_path=db_file.disk_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "FileNotFound", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "ProcessingError", "message": str(exc)})
    except Exception as exc:
        logger.error(
            "PDF OCR failed for file_id={} ({}): {}",
            file_id,
            getattr(db_file, "original_name", "unknown"),
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "OCRError",
                "message": "PDF OCR extraction failed while rendering pages.",
            },
        )

    return result
