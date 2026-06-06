from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ingestion.pdf_ingestor import pdf_ingestor
from backend.core.ingestion.audio_ingestor import audio_ingestor
from backend.core.ingestion.image_processor import image_processor
from backend.database.database import get_session

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

VALID_PDF_TYPES = {"application/pdf"}
VALID_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "audio/mp4",
}
VALID_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/pdf")
async def ingest_pdf(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    content_type = (file.content_type or "").lower()
    if content_type not in VALID_PDF_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "error": "UnsupportedMediaType",
                "message": f"Invalid content type: {file.content_type}. Expected application/pdf",
            },
        )

    file_content = await file.read()

    try:
        result = await pdf_ingestor.ingest_pdf(
            session,
            file_content=file_content,
            original_name=file.filename or "unknown.pdf",
            content_type=content_type,
        )
    except ValueError as exc:
        msg = str(exc)
        if "exceeds" in msg:
            raise HTTPException(
                status_code=413,
                detail={"error": "PayloadTooLarge", "message": msg},
            )
        raise HTTPException(
            status_code=400,
            detail={"error": "ValidationError", "message": msg},
        )

    return result


@router.post("/audio")
async def ingest_audio(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    content_type = (file.content_type or "").lower()
    if content_type not in VALID_AUDIO_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "error": "UnsupportedMediaType",
                "message": f"Invalid content type: {file.content_type}. Expected one of: {', '.join(sorted(VALID_AUDIO_TYPES))}",
            },
        )

    file_content = await file.read()

    try:
        result = await audio_ingestor.ingest_audio(
            session,
            file_content=file_content,
            original_name=file.filename or "unknown.bin",
            content_type=content_type,
        )
    except ValueError as exc:
        msg = str(exc)
        if "exceeds" in msg:
            raise HTTPException(
                status_code=413,
                detail={"error": "PayloadTooLarge", "message": msg},
            )
        raise HTTPException(
            status_code=400,
            detail={"error": "ValidationError", "message": msg},
        )

    return result


@router.post("/image")
async def ingest_image(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    content_type = (file.content_type or "").lower()
    if content_type not in VALID_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "error": "UnsupportedMediaType",
                "message": f"Invalid content type: {file.content_type}. Expected one of: {', '.join(sorted(VALID_IMAGE_TYPES))}",
            },
        )

    file_content = await file.read()

    try:
        result = await image_processor.ingest_image(
            session,
            file_content=file_content,
            original_name=file.filename or "unknown.jpg",
            content_type=content_type,
        )
    except ValueError as exc:
        msg = str(exc)
        if "exceeds" in msg:
            raise HTTPException(
                status_code=413,
                detail={"error": "PayloadTooLarge", "message": msg},
            )
        raise HTTPException(
            status_code=400,
            detail={"error": "ValidationError", "message": msg},
        )

    return result
