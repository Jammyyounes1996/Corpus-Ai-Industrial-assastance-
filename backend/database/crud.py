import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import File, OCRResult, Transcript


async def create_file(
    session: AsyncSession,
    *,
    original_name: str,
    file_type: str,
    disk_path: str,
    size_bytes: int,
    groundx_id: str | None = None,
    qdrant_collection: str | None = None,
) -> File:
    """Create a new file record in the database.

    Raises:
        ValueError: If filename exceeds maximum length (500 chars).
    """
    if len(original_name) > 500:
        raise ValueError(
            f"Filename too long: {len(original_name)} chars (max 500)"
        )
    file_id = str(uuid.uuid4())
    file = File(
        id=file_id,
        original_name=original_name,
        file_type=file_type,
        disk_path=disk_path,
        size_bytes=size_bytes,
        groundx_id=groundx_id,
        qdrant_collection=qdrant_collection,
        indexing_status="pending",
    )
    session.add(file)
    await session.flush()
    return file


async def get_file(session: AsyncSession, file_id: str) -> File | None:
    """Get a file by its ID."""
    result = await session.execute(select(File).where(File.id == file_id))
    return result.scalar_one_or_none()


async def get_files(
    session: AsyncSession,
    *,
    file_type: str = "all",
    sort: str = "date_desc",
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[File], int]:
    """List files with optional filtering and sorting.

    Returns:
        A tuple of (list of files, total count).
    """
    query = select(File)
    count_query = select(func.count()).select_from(File)

    if file_type != "all":
        query = query.where(File.file_type == file_type)
        count_query = count_query.where(File.file_type == file_type)

    if sort == "date_asc":
        query = query.order_by(File.created_at.asc())
    elif sort == "name":
        query = query.order_by(File.original_name.asc())
    else:
        query = query.order_by(File.created_at.desc())

    query = query.limit(limit).offset(offset)

    result = await session.execute(query)
    files = list(result.scalars().all())

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    return files, total


async def update_file_indexing_status(
    session: AsyncSession,
    file_id: str,
    *,
    status: str,
    groundx_id: str | None = None,
    error_message: str | None = None,
) -> File | None:
    """Update the indexing status of a file.

    Valid statuses: pending, processing, indexed, failed.
    """
    file = await get_file(session, file_id)
    if file is None:
        return None

    file.indexing_status = status
    if groundx_id is not None:
        file.groundx_id = groundx_id
    if error_message is not None:
        file.error_message = error_message

    await session.flush()
    return file


async def delete_file(session: AsyncSession, file_id: str) -> bool:
    """Delete a file and all associated records from the database.

    This deletes the File record along with cascaded Transcript and OCRResult.
    Returns True if the file was found and deleted, False otherwise.
    """
    file = await get_file(session, file_id)
    if file is None:
        return False

    await session.delete(file)
    await session.flush()
    return True


async def create_transcript(
    session: AsyncSession,
    *,
    file_id: str,
    transcript_text: str,
    duration_seconds: float,
    language: str,
) -> Transcript:
    """Create a transcript record for an audio file."""
    transcript = Transcript(
        file_id=file_id,
        transcript_text=transcript_text,
        duration_seconds=duration_seconds,
        language=language,
    )
    session.add(transcript)
    await session.flush()
    return transcript


async def get_transcript_by_file_id(
    session: AsyncSession, file_id: str
) -> Transcript | None:
    """Get the transcript for a specific file."""
    result = await session.execute(
        select(Transcript).where(Transcript.file_id == file_id)
    )
    return result.scalar_one_or_none()


async def create_ocr_result(
    session: AsyncSession,
    *,
    file_id: str,
    extracted_text: str,
    model_used: str,
) -> OCRResult:
    """Create an OCR result record for an image file."""
    ocr_result = OCRResult(
        file_id=file_id,
        extracted_text=extracted_text,
        model_used=model_used,
    )
    session.add(ocr_result)
    await session.flush()
    return ocr_result


async def get_ocr_result_by_file_id(
    session: AsyncSession, file_id: str
) -> OCRResult | None:
    """Get the OCR result for a specific file."""
    result = await session.execute(
        select(OCRResult).where(OCRResult.file_id == file_id)
    )
    return result.scalar_one_or_none()
