import asyncio
from pathlib import Path

from groundx import ApiException, Configuration, Groundx
from loguru import logger

from backend.config.settings import get_settings


class GroundXClient:
    """Client for GroundX PDF processing with upload and status polling."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def _get_client(self) -> Groundx:
        config = Configuration(
            api_key=self._settings.GROUNDX_API_KEY,
            api_key_prefix="Bearer",
        )
        return Groundx(configuration=config)

    async def upload_pdf(
        self,
        file_path: str | Path,
        original_name: str,
    ) -> dict:
        """Upload a PDF file to GroundX for indexing.

        Args:
            file_path: Path to the saved PDF file on disk.
            original_name: Original filename from the upload.

        Returns:
            Dict with 'search_id' and 'document_id' from GroundX.

        Raises:
            RuntimeError: If the upload fails.
        """
        file_path = Path(file_path)
        client = self._get_client()

        try:
            with open(file_path, "rb") as f:
                response = client.documents.ingest_local(
                    body={
                        "documents": [
                            {
                                "bucketId": str(self._settings.GROUNDX_BUCKET_ID),
                                "fileName": original_name,
                                "fileData": f,
                                "contentType": "application/pdf",
                            }
                        ]
                    }
                )

            ingest_data = response
            logger.info(
                "GroundX upload successful for '{}': {}",
                original_name,
                ingest_data,
            )

            search_id = None
            document_id = None

            if hasattr(ingest_data, "body") and ingest_data.body:
                body = ingest_data.body
                if isinstance(body, dict):
                    search_id = body.get("searchId") or body.get("search_id")
                    document_id = body.get("documentId") or body.get("document_id")
                    ingest = body.get("ingest") or {}
                    if not search_id:
                        search_id = ingest.get("searchId") or ingest.get("search_id")
                    if not document_id:
                        docs = ingest.get("documents") or []
                        if docs:
                            document_id = (
                                docs[0].get("documentId")
                                or docs[0].get("document_id")
                            )

            return {
                "search_id": search_id,
                "document_id": document_id,
            }

        except ApiException as exc:
            logger.error("GroundX API error uploading '{}': {}", original_name, exc)
            raise RuntimeError(f"GroundX upload failed: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error uploading '{}' to GroundX: {}", original_name, exc)
            raise RuntimeError(f"GroundX upload failed: {exc}") from exc

    async def poll_indexing_status(
        self,
        document_id: str,
        max_wait: int = 300,
        poll_interval: int = 2,
    ) -> dict:
        """Poll GroundX for document indexing status.

        Args:
            document_id: The GroundX document ID to check.
            max_wait: Maximum seconds to wait (default 300 = 5 min).
            poll_interval: Seconds between polls (default 2).

        Returns:
            Dict with 'status' ("complete" or "error") and optional 'error_message'.

        Raises:
            TimeoutError: If indexing doesn't complete within max_wait.
            RuntimeError: If the poll request fails.
        """
        client = self._get_client()
        elapsed = 0

        while elapsed < max_wait:
            try:
                response = client.documents.get_processing_status_by_id(
                    document_id=document_id,
                )

                status = None
                if hasattr(response, "body") and response.body:
                    body = response.body if isinstance(response.body, dict) else {}
                    doc = body.get("document") or body
                    status = doc.get("status", "").lower()

                logger.debug("GroundX poll for doc {}: status={}", document_id, status)

                if status in ("complete", "completed", "indexed"):
                    return {"status": "complete"}

                if status in ("error", "failed"):
                    error_msg = ""
                    if isinstance(response.body, dict):
                        doc = response.body.get("document") or response.body
                        error_msg = doc.get("error", "Unknown error")
                    return {"status": "error", "error_message": error_msg}

            except ApiException as exc:
                logger.warning("GroundX poll API error for doc {}: {}", document_id, exc)

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"GroundX indexing timed out after {max_wait}s for document {document_id}"
        )


groundx_client = GroundXClient()
