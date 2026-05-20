from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import crud
from backend.database.database import get_session
from backend.schemas.ingest import ErrorResponse

router = APIRouter(prefix="/api/files", tags=["files"])


def _file_to_dict(file: object) -> dict:
    """Convert a File ORM object to a dict with enriched metadata."""
    data = {
        "id": file.id,
        "original_name": file.original_name,
        "file_type": file.file_type,
        "size_bytes": file.size_bytes,
        "indexing_status": file.indexing_status,
        "error_message": file.error_message,
        "created_at": file.created_at.isoformat() if file.created_at else None,
    }

    if file.transcript:
        data["transcript_summary"] = {
            "duration_seconds": file.transcript.duration_seconds,
            "language": file.transcript.language,
        }

    if file.ocr_result:
        text = file.ocr_result.extracted_text
        data["ocr_summary"] = {
            "text_preview": text[:200] if text else "",
            "model_used": file.ocr_result.model_used,
        }

    return data


@router.get("")
async def list_files(
    type: str = Query("all", description="Filter by type: all, pdf, audio, image"),
    sort: str = Query("date_desc", description="Sort: date_desc, date_asc, name"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List files with optional filtering, sorting, and pagination.

    Returns enriched file metadata including transcript/OCR summaries.
    """
    valid_types = {"all", "pdf", "audio", "image"}
    if type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail={"error": "InvalidFilter", "message": f"type must be one of: {', '.join(sorted(valid_types))}"},
        )

    valid_sorts = {"date_desc", "date_asc", "name"}
    if sort not in valid_sorts:
        raise HTTPException(
            status_code=400,
            detail={"error": "InvalidSort", "message": f"sort must be one of: {', '.join(sorted(valid_sorts))}"},
        )

    files, total = await crud.get_files(
        session,
        file_type=type,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    return {
        "files": [_file_to_dict(f) for f in files],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def _qdrant_collection_exists(collection: str) -> bool:
    """Check if Qdrant collection exists."""
    from qdrant_client import QdrantClient
    from backend.config.settings import get_settings

    settings = get_settings()
    client = QdrantClient(url=settings.QDRANT_URL)

    try:
        client.get_collection(collection)
        return True
    except Exception:
        return False


@router.delete(
    "/{file_id}",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def delete_file_endpoint(
    file_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete a file and all associated data atomically with rollback.

    Removes from: disk storage, database (File, Transcript, OCRResult), Qdrant chunks.
    Uses transaction pattern with rollback on failure.

    Raises:
        HTTPException: 404 if file not found
        HTTPException: 500 if deletion fails
    """
    db_file = await crud.get_file(session, file_id)
    if db_file is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NotFound", "message": f"File not found: {file_id}"},
        )

    disk_path = db_file.disk_path
    qdrant_collection = db_file.qdrant_collection

    # Pre-flight validation: check if we can delete from each location
    can_delete_disk = False
    can_delete_qdrant = False
    can_delete_db = True

    if not qdrant_collection:
        # No Qdrant data to delete
        can_delete_qdrant = True
    elif await _qdrant_collection_exists(qdrant_collection):
        can_delete_qdrant = True
    else:
        logger.warning(
            "Qdrant collection {} does not exist, skipping Qdrant deletion",
            qdrant_collection,
        )
        can_delete_qdrant = True

    if disk_path:
        path = Path(disk_path)
        can_delete_disk = path.exists() and not path.is_file()
    else:
        can_delete_disk = True

    if not (can_delete_disk and can_delete_qdrant and can_delete_db):
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DeletionError",
                "message": "Cannot proceed with deletion - pre-flight checks failed",
                "details": {
                    "disk": can_delete_disk,
                    "qdrant": can_delete_qdrant,
                    "database": can_delete_db,
                },
            },
        )

    qdrant_deleted = False
    disk_deleted = False
    db_deleted = False

    try:
        # Step 1: Delete from Qdrant (no rollback possible)
        if qdrant_collection and can_delete_qdrant:
            await _delete_qdrant_chunks(file_id, qdrant_collection)
            qdrant_deleted = True
            logger.info("Qdrant chunks deleted for file {}", file_id)

        # Step 2: Delete from database (can rollback)
        await crud.delete_file(session, file_id)
        db_deleted = True
        await session.flush()
        logger.info("Database records deleted for file {}", file_id)

        # Step 3: Delete from disk (cannot rollback)
        if can_delete_disk:
            path = Path(disk_path)
            path.unlink()
            disk_deleted = True
            logger.info("Disk file deleted for file {}", file_id)

        # All successful - commit transaction
        await session.commit()

        logger.info(
            "Successfully deleted file {} (disk={}, db={}, qdrant={})",
            file_id,
            disk_deleted,
            db_deleted,
            qdrant_deleted,
        )

        return {"status": "deleted", "file_id": file_id}

    except Exception as exc:
        # Rollback database if it was flushed
        logger.error("Deletion failed for file {}, attempting rollback", file_id, exc)
        try:
            if db_deleted:
                await session.rollback()
        except Exception as rollback_exc:
            logger.error("Failed to rollback database for file {}", file_id, rollback_exc)

        raise HTTPException(
            status_code=500,
            detail={"error": "DeletionError", "message": f"Failed to delete file: {exc}"},
        )


async def _delete_qdrant_chunks(file_id: str, collection: str) -> None:
    """Delete all Qdrant chunks for a given file_id using scroll API."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    from backend.config.settings import get_settings

    settings = get_settings()
    client = QdrantClient(url=settings.QDRANT_URL)

    client.delete(
        collection_name=collection,
        points_selector=Filter(
            must=[FieldCondition(key="file_id", match=MatchValue(value=file_id))],
        ),
    )
    logger.info("Deleted Qdrant chunks for file {} from {}", file_id, collection)
