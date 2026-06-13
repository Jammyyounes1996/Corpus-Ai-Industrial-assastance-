import asyncio
from pathlib import Path

from groundx import Groundx, ApiException
from groundx.model.document_local_ingest_request_item import DocumentLocalIngestRequestItem
from groundx.model.document_local_ingest_request_item_metadata import DocumentLocalIngestRequestItemMetadata
from loguru import logger

from backend.config.settings import get_settings


def _body_dict(response: object) -> dict:
    body = getattr(response, "body", response)
    return body if isinstance(body, dict) else {}


def _first_progress_document(progress: dict) -> tuple[str, dict]:
    for bucket_name in ("errors", "complete", "processing", "queued", "cancelled"):
        bucket = progress.get(bucket_name) or {}
        documents = bucket.get("documents") or []
        if documents:
            return bucket_name, documents[0]
    return "", {}


class GroundXClient:
    """Client for GroundX PDF processing with upload and status polling."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def _get_client(self) -> Groundx:
        return Groundx(api_key=self._settings.GROUNDX_API_KEY)

    def _normalize_processing_payload(self, payload: dict) -> dict:
        ingest = payload.get("ingest") or {}
        progress = ingest.get("progress") or {}
        bucket_name, document = _first_progress_document(progress)
        top_status = str(ingest.get("status") or "").lower()
        document_status = str(document.get("status") or "").lower()
        raw_status = document_status or top_status

        if bucket_name == "errors" or raw_status in {"error", "failed", "cancelled"}:
            app_status = "failed"
        elif bucket_name == "complete" or raw_status == "complete":
            app_status = "indexed"
        elif bucket_name == "queued" or raw_status == "queued":
            app_status = "queued"
        elif bucket_name == "processing" or raw_status in {"processing", "training"} or top_status == "training":
            app_status = "processing"
        else:
            app_status = "processing"

        return {
            "status": app_status,
            "raw_status": raw_status or top_status,
            "process_id": str(document.get("processId") or ingest.get("processId") or "") or None,
            "document_id": str(document.get("documentId") or "") or None,
            "bucket_id": str(document.get("bucketId") or "") or None,
            "status_message": document.get("statusMessage") or ingest.get("statusMessage") or None,
            "error_message": document.get("statusMessage") or ingest.get("error") or None,
            "document": document,
        }

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
            ingest_data = _body_dict(response)
            logger.info(
                "GroundX upload successful for '{}': {}",
                original_name,
                ingest_data,
            )
            normalized = self._normalize_processing_payload(ingest_data)
            if not normalized.get("status_message"):
                normalized["status_message"] = "Queued for GroundX indexing"
            return normalized

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

                normalized = self._normalize_processing_payload(_body_dict(response))
                status = normalized["status"]

                logger.debug("GroundX poll for process {}: status={}", process_id, status)

                if status == "indexed":
                    return normalized

                if status == "failed":
                    return normalized

            except ApiException as exc:
                logger.warning("GroundX poll API error for process {}: {}", process_id, exc)

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"GroundX indexing timed out after {max_wait}s for process {process_id}"
        )

    async def get_processing_status(self, process_id: str) -> dict:
        client = self._get_client()

        try:
            response = client.documents.get_processing_status_by_id(process_id=process_id)
            return self._normalize_processing_payload(_body_dict(response))
        except ApiException as exc:
            logger.error("GroundX status API error for process {}: {}", process_id, exc)
            raise RuntimeError(f"GroundX status check failed: {exc}") from exc
        except Exception as exc:
            logger.error("GroundX status unexpected error for process {}: {}", process_id, exc)
            raise RuntimeError(f"GroundX status check failed: {exc}") from exc


    async def search(self, query: str, n_results: int = 5) -> dict:
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
            search_data = _body_dict(response)
            search_obj = search_data.get("search", {})
            search_text = search_obj.get("text", "") or ""
            chunks = search_obj.get("results", [])

            for chunk in chunks[:n_results]:
                results.append({
                    "content": chunk.get("text") or chunk.get("suggestedText", ""),
                    "score": float(chunk.get("score", 0.0)),
                    "file_name": chunk.get("fileName", ""),
                    "source": chunk.get("sourceUrl") or chunk.get("fileName") or "groundx",
                    "document_id": str(chunk.get("documentId", "") or "") or None,
                    "source_url": chunk.get("sourceUrl"),
                    "suggested_text": chunk.get("suggestedText"),
                    "excerpt": chunk.get("text") or chunk.get("suggestedText", ""),
                    "bucket_id": str(self._settings.GROUNDX_BUCKET_ID),
                    "provider": "groundx",
                })

            logger.info(
                "GroundX search for '{}': {} results",
                query[:80],
                len(results),
            )
            return {
                "text": search_text,
                "results": results,
            }

        except ApiException as exc:
            logger.error("GroundX search API error: {}", exc)
            raise RuntimeError(f"GroundX search failed: {exc}") from exc
        except Exception as exc:
            logger.error("GroundX search unexpected error: {}", exc)
            raise RuntimeError(f"GroundX search failed: {exc}") from exc


groundx_client = GroundXClient()
