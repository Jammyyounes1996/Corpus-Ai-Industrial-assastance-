import asyncio
from pathlib import Path

from groundx import Groundx, ApiException
from groundx.model.document_local_ingest_request_item import DocumentLocalIngestRequestItem
from groundx.model.document_local_ingest_request_item_metadata import DocumentLocalIngestRequestItemMetadata
from loguru import logger

from backend.config.settings import get_settings


class GroundXClient:
    """Client for GroundX PDF processing with upload and status polling."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def _get_client(self) -> Groundx:
        return Groundx(api_key=self._settings.GROUNDX_API_KEY)

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
            Dict with 'process_id' and 'status' from GroundX.

        Raises:
            RuntimeError: If the upload fails.
        """
        file_path = Path(file_path)
        client = self._get_client()

        try:
            metadata = DocumentLocalIngestRequestItemMetadata(
                fileName=original_name,
                bucketId=int(self._settings.GROUNDX_BUCKET_ID),  # ← int() مهمة
                fileType="pdf",
            )

            with open(file_path, "rb") as f:
                document = DocumentLocalIngestRequestItem(
                    metadata=metadata,
                    blob=f,
                )

                response = client.documents.ingest_local(
                    body=[document]
                )
            ingest_data = response.body
            logger.info(
                "GroundX upload successful for '{}': {}",
                original_name,
                ingest_data,
            )

            process_id = None
            status = None

            if isinstance(ingest_data, dict) and "ingest" in ingest_data:
                ingest = ingest_data["ingest"]
                process_id = ingest.get("processId")
                status = ingest.get("status")

            return {
                "process_id": process_id,
                "status": status,
                "document_id": None,  # Will be populated after processing completes
            }

        except ApiException as exc:
            logger.error("GroundX API error uploading '{}': {}", original_name, exc)
            raise RuntimeError(f"GroundX upload failed: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error uploading '{}' to GroundX: {}", original_name, exc)
            raise RuntimeError(f"GroundX upload failed: {exc}") from exc

    async def poll_indexing_status(
        self,
        process_id: str,
        max_wait: int = 300,
        poll_interval: int = 2,
    ) -> dict:
        """Poll GroundX for document indexing status.

        Args:
            process_id: The GroundX process ID from the ingest response.
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
                    process_id=process_id,
                )

                status = None
                if isinstance(response.body, dict):
                    ingest = response.body.get("ingest") or {}
                    status = ingest.get("status", "").lower()

                logger.debug("GroundX poll for process {}: status={}", process_id, status)

                if status in ("complete", "completed"):
                    return {"status": "complete"}

                if status in ("error", "failed"):
                    error_msg = ""
                    if isinstance(response.body, dict):
                        ingest = response.body.get("ingest") or {}
                        error_msg = ingest.get("error", "Unknown error")
                    return {"status": "error", "error_message": error_msg}

            except ApiException as exc:
                logger.warning("GroundX poll API error for process {}: {}", process_id, exc)

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"GroundX indexing timed out after {max_wait}s for process {process_id}"
        )


    async def search(self, query: str, n_results: int = 5) -> list[dict]:
        """Search indexed documents in GroundX for relevant content.

        Args:
            query: Natural language search query.
            n_results: Maximum number of results to return.

        Returns:
            List of dicts with keys: content, score, file_name, chunk_id.

        Raises:
            RuntimeError: If the search request fails.
        """
        client = self._get_client()

        try:
            response = client.search.content(
                id=int(self._settings.GROUNDX_BUCKET_ID),
                query=query,
            )

            results: list[dict] = []
            search_data = response.body if hasattr(response, "body") else {}
            search_obj = search_data.get("search", {})
            chunks = search_obj.get("results", [])

            for chunk in chunks[:n_results]:
                results.append({
                    "content": chunk.get("text", ""),
                    "score": float(chunk.get("score", 0.0)),
                    "file_name": chunk.get("fileName", ""),
                    "chunk_id": str(chunk.get("chunkId", "")),
                })

            logger.info(
                "GroundX search for '{}': {} results",
                query[:80],
                len(results),
            )
            return results

        except ApiException as exc:
            logger.error("GroundX search API error: {}", exc)
            raise RuntimeError(f"GroundX search failed: {exc}") from exc
        except Exception as exc:
            logger.error("GroundX search unexpected error: {}", exc)
            raise RuntimeError(f"GroundX search failed: {exc}") from exc


groundx_client = GroundXClient()
