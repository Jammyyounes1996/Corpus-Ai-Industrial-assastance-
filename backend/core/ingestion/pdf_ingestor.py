import uuid
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.core.retrieval.groundx_client import groundx_client
from backend.database import crud


class PDFIngestor:
    """Handles PDF ingestion: save to disk, upload to GroundX, poll status, persist to DB."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._upload_dir = Path("data/uploads")
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def ingest_pdf(
        self,
        session: AsyncSession,
        *,
        file_content: bytes,
        original_name: str,
        content_type: str,
    ) -> dict:
        """Ingest a PDF file: save, upload to GroundX, and create DB record.

        Args:
            session: Async database session.
            file_content: Raw PDF file bytes.
            original_name: Original filename.
            content_type: MIME type from upload.

        Returns:
            Dict with file_id, filename, status, size_bytes.

        Raises:
            ValueError: If file validation fails.
            RuntimeError: If GroundX upload fails.
        """
        if content_type != "application/pdf":
            raise ValueError(f"Invalid content type: {content_type}. Expected application/pdf")

        size_bytes = len(file_content)
        if size_bytes > self._settings.max_pdf_size_bytes:
            raise ValueError(
                f"File size ({size_bytes / (1024*1024):.1f} MB) exceeds "
                f"maximum ({self._settings.MAX_PDF_SIZE_MB} MB) for PDF files"
            )

        file_uuid = str(uuid.uuid4())
        disk_path = self._upload_dir / f"{file_uuid}.pdf"

        with open(disk_path, "wb") as f:
            f.write(file_content)
        logger.info("Saved PDF '{}' to {}", original_name, disk_path)

        db_file = await crud.create_file(
            session,
            original_name=original_name,
            file_type="pdf",
            disk_path=str(disk_path),
            size_bytes=size_bytes,
        )

        try:
            result = await groundx_client.upload_pdf(disk_path, original_name)

            groundx_doc_id = result.get("document_id")
            if groundx_doc_id:
                await crud.update_file_indexing_status(
                    session,
                    db_file.id,
                    status="processing",
                    groundx_id=str(groundx_doc_id),
                )
                logger.info(
                    "PDF '{}' uploaded to GroundX, doc_id={}",
                    original_name,
                    groundx_doc_id,
                )
            else:
                await crud.update_file_indexing_status(
                    session,
                    db_file.id,
                    status="processing",
                )
                logger.warning(
                    "PDF '{}' uploaded to GroundX but no document_id returned",
                    original_name,
                )

            return {
                "file_id": db_file.id,
                "filename": original_name,
                "status": "processing",
                "size_bytes": size_bytes,
            }

        except Exception as exc:
            await crud.update_file_indexing_status(
                session,
                db_file.id,
                status="failed",
                error_message=str(exc),
            )
            logger.error("Failed to ingest PDF '{}': {}", original_name, exc)
            raise

    async def check_indexing_status(
        self,
        session: AsyncSession,
        file_id: str,
    ) -> dict:
        """Check GroundX indexing status and update DB record.

        Args:
            session: Async database session.
            file_id: The file ID to check.

        Returns:
            Dict with current status information.

        Raises:
            ValueError: If file not found or has no GroundX document ID.
        """
        db_file = await crud.get_file(session, file_id)
        if db_file is None:
            raise ValueError(f"File not found: {file_id}")

        if not db_file.groundx_id:
            raise ValueError(f"File {file_id} has no GroundX document ID")

        try:
            result = await groundx_client.poll_indexing_status(
                document_id=db_file.groundx_id,
            )

            status = result["status"]
            if status == "complete":
                await crud.update_file_indexing_status(
                    session, file_id, status="indexed"
                )
                return {"file_id": file_id, "status": "indexed"}
            else:
                error_msg = result.get("error_message", "Unknown error")
                await crud.update_file_indexing_status(
                    session, file_id, status="failed", error_message=error_msg
                )
                return {"file_id": file_id, "status": "failed", "error": error_msg}

        except TimeoutError as exc:
            await crud.update_file_indexing_status(
                session, file_id, status="failed", error_message=str(exc)
            )
            return {"file_id": file_id, "status": "failed", "error": str(exc)}


pdf_ingestor = PDFIngestor()
