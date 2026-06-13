import uuid
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.core.retrieval.groundx_client import groundx_client
from backend.database import crud


GROUNDX_READY_MESSAGE = "Ready for GroundX retrieval"
GROUNDX_QUEUED_MESSAGE = "Queued for GroundX indexing"
GROUNDX_PROCESSING_MESSAGE = "Processing in GroundX"
GROUNDX_FAILED_MESSAGE = "GroundX indexing failed"


class PDFIngestor:
    """Handles PDF ingestion: save to disk, upload to GroundX, poll status, persist to DB."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._upload_dir = Path("data/uploads")
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def _status_message_for(self, status: str, fallback: str | None = None) -> str | None:
        if status == "indexed":
            return GROUNDX_READY_MESSAGE
        if status == "queued":
            return GROUNDX_QUEUED_MESSAGE
        if status == "processing":
            return GROUNDX_PROCESSING_MESSAGE
        if status == "failed":
            return fallback or GROUNDX_FAILED_MESSAGE
        return fallback

    def build_status_payload(self, db_file) -> dict:
        status = db_file.indexing_status or "pending"
        return {
            "file_id": db_file.id,
            "original_name": db_file.original_name,
            "file_type": db_file.file_type,
            "mime_type": "application/pdf" if db_file.file_type == "pdf" else None,
            "indexing_status": status,
            "groundx_process_id": db_file.groundx_process_id,
            "groundx_document_id": db_file.groundx_document_id,
            "groundx_bucket_id": db_file.groundx_bucket_id,
            "status_message": db_file.status_message,
            "error_message": db_file.error_message,
            "ready_for_groundx_retrieval": status == "indexed",
        }

    async def refresh_groundx_status(self, session: AsyncSession, file_id: str) -> dict:
        db_file = await crud.get_file(session, file_id)
        if db_file is None:
            raise ValueError(f"File not found: {file_id}")

        if db_file.indexing_status in {"indexed", "failed"}:
            return self.build_status_payload(db_file)

        if not db_file.groundx_process_id:
            db_file.status_message = db_file.status_message or "GroundX process has not started"
            await session.flush()
            return self.build_status_payload(db_file)

        status = await groundx_client.get_processing_status(db_file.groundx_process_id)
        logger.info(
            "GroundX status polled: file_id={} process_id={} status={}",
            file_id,
            db_file.groundx_process_id,
            status.get("status", "unknown"),
        )

        next_status = status["status"]
        next_status_message = self._status_message_for(next_status, status.get("status_message"))
        next_error = status.get("error_message") if next_status == "failed" else None

        await crud.update_file_indexing_status(
            session,
            file_id,
            status=next_status,
            groundx_process_id=status.get("process_id"),
            groundx_document_id=status.get("document_id"),
            groundx_bucket_id=status.get("bucket_id") or str(self._settings.GROUNDX_BUCKET_ID),
            status_message=next_status_message,
            error_message=next_error,
        )

        refreshed = await crud.get_file(session, file_id)
        if refreshed is None:
            raise ValueError(f"File not found after status refresh: {file_id}")
        return self.build_status_payload(refreshed)

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

            process_id = result.get("process_id")
            initial_status = result.get("status") or "queued"
            if initial_status not in {"queued", "processing", "indexed", "failed"}:
                initial_status = "queued"

            await crud.update_file_indexing_status(
                session,
                db_file.id,
                status=initial_status,
                groundx_id=str(process_id) if process_id else None,
                groundx_process_id=str(process_id) if process_id else None,
                groundx_document_id=result.get("document_id"),
                groundx_bucket_id=result.get("bucket_id") or str(self._settings.GROUNDX_BUCKET_ID),
                status_message=self._status_message_for(initial_status, result.get("status_message")),
                error_message=result.get("error_message") if initial_status == "failed" else None,
            )

            logger.info(
                "GroundX ingest started: file_id={} bucket_id={}",
                db_file.id,
                result.get("bucket_id") or str(self._settings.GROUNDX_BUCKET_ID),
            )
            if process_id:
                logger.info("GroundX process_id saved: file_id={} process_id={}", db_file.id, process_id)

            return {
                "file_id": db_file.id,
                "filename": original_name,
                "file_type": "pdf",
                "size": size_bytes,
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "status": initial_status,
                "indexing_status": initial_status,
                "status_message": self._status_message_for(initial_status, result.get("status_message")),
                "groundx_process_id": str(process_id) if process_id else None,
                "groundx_bucket_id": result.get("bucket_id") or str(self._settings.GROUNDX_BUCKET_ID),
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

    async def save_pdf_only(
        self,
        session: AsyncSession,
        *,
        file_content: bytes,
        original_name: str,
        content_type: str,
    ) -> dict:
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
        logger.info("Saved PDF '{}' to {} (OCR-only, no GroundX)", original_name, disk_path)

        db_file = await crud.create_file(
            session,
            original_name=original_name,
            file_type="pdf",
            disk_path=str(disk_path),
            size_bytes=size_bytes,
        )

        return {
            "file_id": db_file.id,
            "filename": original_name,
            "file_type": "pdf",
            "size": size_bytes,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
        }

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

        if not db_file.groundx_process_id:
            raise ValueError(f"File {file_id} has no GroundX process ID")

        try:
            result = await groundx_client.get_processing_status(
                process_id=db_file.groundx_process_id,
            )

            status = result["status"]
            await crud.update_file_indexing_status(
                session,
                file_id,
                status=status,
                groundx_process_id=result.get("process_id"),
                groundx_document_id=result.get("document_id"),
                groundx_bucket_id=result.get("bucket_id") or db_file.groundx_bucket_id,
                status_message=self._status_message_for(status, result.get("status_message")),
                error_message=result.get("error_message") if status == "failed" else None,
            )
            return self.build_status_payload((await crud.get_file(session, file_id)) or db_file)

        except TimeoutError as exc:
            await crud.update_file_indexing_status(
                session, file_id, status="failed", error_message=str(exc)
            )
            return {"file_id": file_id, "status": "failed", "error": str(exc)}


pdf_ingestor = PDFIngestor()
