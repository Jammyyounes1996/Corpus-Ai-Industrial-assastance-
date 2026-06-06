import uuid
import json
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from backend.database.models import Chat, File, Message, OCRResult, Transcript, EvaluationResult


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
    result = await session.execute(
        select(File)
        .options(
            selectinload(File.transcript),
            selectinload(File.ocr_result),
        )
        .where(File.id == file_id)
    )
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
    query = select(File).options(
        selectinload(File.transcript),
        selectinload(File.ocr_result),
    )
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
    files = list(result.scalars().unique().all())

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


async def get_files_by_ids(session: AsyncSession, file_ids: list[str]) -> list[File]:
    """Get files by a list of IDs using a single query."""
    if not file_ids:
        return []

    result = await session.execute(
        select(File)
        .options(
            selectinload(File.transcript),
            selectinload(File.ocr_result),
        )
        .where(File.id.in_(file_ids))
    )
    return list(result.scalars().unique().all())


async def create_chat(
    session: AsyncSession,
    *,
    title: str,
    model_provider: str,
    model_name: str,
) -> Chat:
    """Create a new chat record."""
    logger.info(f"Creating chat with title: {title[:50]}")
    chat = Chat(
        title=title,
        model_provider=model_provider,
        model_name=model_name,
    )
    session.add(chat)
    await session.flush()
    return chat


async def get_chat(session: AsyncSession, chat_id: str) -> Chat | None:
    """Get a chat by its ID."""
    logger.info(f"Retrieving chat: {chat_id}")
    result = await session.execute(
        select(Chat)
        .options(selectinload(Chat.messages))
        .where(Chat.id == chat_id)
    )
    return result.scalar_one_or_none()


async def get_chats(
    session: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Chat]:
    """List chats ordered by most recently updated."""
    result = await session.execute(
        select(Chat)
        .order_by(Chat.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def _count_chat_messages(session: AsyncSession, chat_id: str) -> int:
    """Count messages for a chat."""
    result = await session.execute(
        select(func.count()).select_from(Message).where(Message.chat_id == chat_id)
    )
    return int(result.scalar() or 0)


async def delete_chat(session: AsyncSession, chat_id: str) -> bool:
    """Delete a chat by ID."""
    logger.info(f"Deleting chat: {chat_id}")
    chat = await get_chat(session, chat_id)
    if chat is None:
        return False

    await session.delete(chat)
    await session.flush()
    return True


async def create_message(
    session: AsyncSession,
    *,
    chat_id: str,
    role: str,
    content: str,
    thinking_steps: str | None = None,
    retrieved_context: str | None = None,
    attached_files: list[str] | None = None,
) -> Message:
    """Create a new message in a chat."""
    attached_files = json.dumps(attached_files or [])
    message = Message(
        chat_id=chat_id,
        role=role,
        content=content,
        thinking_steps=thinking_steps,
        retrieved_context=retrieved_context,
        attached_files=attached_files,
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    return message


async def get_messages(
    session: AsyncSession,
    *,
    chat_id: str,
    limit: int = 100,
) -> list[Message]:
    """Get chat messages ordered by creation time."""
    return await get_chat_messages(session, chat_id=chat_id, limit=limit)


async def get_chat_messages(
    session: AsyncSession,
    *,
    chat_id: str,
    limit: int = 100,
) -> list[Message]:
    """Get chat messages ordered by creation time with pagination limit."""
    result = await session.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_message_content(
    session: AsyncSession,
    message_id: str,
    *,
    content: str,
    thinking_steps: str | None = None,
    retrieved_context: str | None = None,
) -> Message | None:
    """Update an existing message content."""
    result = await session.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    if message is None:
        return None

    message.content = content
    if thinking_steps is not None:
        message.thinking_steps = thinking_steps
    if retrieved_context is not None:
        message.retrieved_context = retrieved_context
    await session.commit()
    await session.refresh(message)
    return message


async def summarize_old_messages(
    session: AsyncSession,
    chat_id: str,
    llm,
    summarize_count: int = 40,
) -> bool:
    """
    Summarizes the oldest `summarize_count` messages in a chat.
    Deletes them and inserts one summary Message in their place.
    Returns True if summarization was performed, False if skipped.
    """
    result = await session.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .limit(summarize_count)
    )
    old_messages = result.scalars().all()

    if len(old_messages) < summarize_count:
        return False

    old_ids = [m.id for m in old_messages]

    conversation_text = "\n".join(f"{m.role}: {m.content}" for m in old_messages)

    summary_response = await llm.ainvoke(
        f"Summarize this technical conversation concisely, "
        f"preserving key facts, decisions, and context:\n\n"
        f"{conversation_text}"
    )
    summary_text = summary_response.content

    await session.execute(sa_delete(Message).where(Message.id.in_(old_ids)))

    summary_message = Message(
        chat_id=chat_id,
        role="system",
        content=f"[CONVERSATION SUMMARY]: {summary_text}",
        thinking_steps=None,
        retrieved_context=None,
        attached_files=None,
    )
    session.add(summary_message)
    await session.commit()

    return True


async def create_evaluation(
    session: AsyncSession,
    *,
    chat_id: str,
    message_id: int,
    faithfulness: float | None = None,
    answer_relevancy: float | None = None,
    model_used: str | None = None,
) -> EvaluationResult:
    eval_result = EvaluationResult(
        chat_id=chat_id,
        message_id=message_id,
        faithfulness=faithfulness,
        answer_relevancy=answer_relevancy,
        model_used=model_used,
    )
    session.add(eval_result)
    await session.flush()
    await session.refresh(eval_result)
    return eval_result


async def get_evaluations(
    session: AsyncSession,
    *,
    chat_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[EvaluationResult], int]:
    query = select(EvaluationResult)
    count_query = select(func.count()).select_from(EvaluationResult)

    if chat_id:
        query = query.where(EvaluationResult.chat_id == chat_id)
        count_query = count_query.where(EvaluationResult.chat_id == chat_id)

    query = query.order_by(EvaluationResult.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    evaluations = list(result.scalars().all())

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    return evaluations, total


async def get_evaluation_by_message(
    session: AsyncSession,
    message_id: int,
) -> EvaluationResult | None:
    result = await session.execute(
        select(EvaluationResult).where(EvaluationResult.message_id == message_id)
    )
    return result.scalar_one_or_none()
