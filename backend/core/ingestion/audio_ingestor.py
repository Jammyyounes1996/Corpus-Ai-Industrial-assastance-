from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from faster_whisper import WhisperModel
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.core.ingestion.chunking import chunk_text
from backend.core.models.ollama_client import ollama_client
from backend.database import crud


class AudioIngestor:
    """Handles audio ingestion: save, transcribe, chunk, embed, store in Qdrant."""

    ALLOWED_MIME_TYPES: set[str] = {
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/m4a",
        "audio/x-m4a",
        "audio/ogg",
        "audio/mp4",
    }

    def __init__(self) -> None:
        self._settings = get_settings()
        self._upload_dir = Path("data/uploads")
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._model: WhisperModel | None = None

    def _get_device(self) -> str:
        """Detect best device for Whisper inference."""
        setting = self._settings.WHISPER_DEVICE
        if setting != "auto":
            return setting
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def _get_compute_type(self, device: str) -> str:
        """Select compute type based on device."""
        if device == "cpu":
            return "int8"
        if device == "cuda":
            return "float16"

        setting = self._settings.WHISPER_COMPUTE_TYPE
        if setting != "auto":
            return setting
        return "float16"

    def _get_whisper_model(self) -> WhisperModel:
        """Lazy-load the Whisper model."""
        if self._model is None:
            device = self._get_device()
            compute_type = self._get_compute_type(device)
            model_name = self._settings.WHISPER_MODEL
            logger.info(
                "Loading Whisper model '{}' on '{}' with compute_type='{}'",
                model_name,
                device,
                compute_type,
            )
            self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
        return self._model

    def _validate_audio(self, content_type: str, size_bytes: int) -> None:
        """Validate audio file MIME type and size."""
        if content_type.lower() not in {m.lower() for m in self.ALLOWED_MIME_TYPES}:
            raise ValueError(
                f"Invalid content type: {content_type}. "
                f"Expected one of: {', '.join(sorted(self.ALLOWED_MIME_TYPES))}"
            )
        if size_bytes > self._settings.max_audio_size_bytes:
            raise ValueError(
                f"File size ({size_bytes / (1024*1024):.1f} MB) exceeds "
                f"maximum ({self._settings.MAX_AUDIO_SIZE_MB} MB) for audio files"
            )

    async def ingest_audio(
        self,
        session: AsyncSession,
        *,
        file_content: bytes,
        original_name: str,
        content_type: str,
    ) -> dict:
        """Full audio ingestion pipeline.

        1. Validate and save to disk
        2. Transcribe with Faster-Whisper
        3. Chunk the transcript
        4. Embed chunks with Ollama
        5. Insert chunks into Qdrant
        6. Persist metadata to DB

        Returns:
            Dict with file_id, filename, status, size_bytes, duration_seconds, language.
        """
        size_bytes = len(file_content)
        self._validate_audio(content_type, size_bytes)

        file_uuid = str(uuid.uuid4())
        ext = Path(original_name).suffix or ".bin"
        disk_path = self._upload_dir / f"{file_uuid}{ext}"

        with open(disk_path, "wb") as f:
            f.write(file_content)
        logger.info("Saved audio '{}' to {}", original_name, disk_path)

        db_file = await crud.create_file(
            session,
            original_name=original_name,
            file_type="audio",
            disk_path=str(disk_path),
            size_bytes=size_bytes,
            qdrant_collection=self._settings.QDRANT_COLLECTION,
        )

        try:
            transcript_text, duration_seconds, language = self._transcribe(disk_path)

            await crud.create_transcript(
                session,
                file_id=db_file.id,
                transcript_text=transcript_text,
                duration_seconds=duration_seconds,
                language=language,
            )

            chunks = chunk_text(transcript_text, max_tokens=500, overlap_fraction=0.1)
            logger.info("Audio '{}' chunked into {} segments", original_name, len(chunks))

            embeddings = await ollama_client.embed_texts(chunks)

            await self._insert_chunks_to_qdrant(
                file_id=db_file.id,
                chunks=chunks,
                embeddings=embeddings,
            )

            await crud.update_file_indexing_status(session, db_file.id, status="indexed")

            return {
                "file_id": db_file.id,
                "filename": original_name,
                "status": "indexed",
                "size_bytes": size_bytes,
                "duration_seconds": round(duration_seconds, 2),
                "language": language,
            }

        except Exception as exc:
            await crud.update_file_indexing_status(
                session, db_file.id, status="failed", error_message=str(exc)
            )
            logger.error("Failed to ingest audio '{}': {}", original_name, exc)
            raise

    def _transcribe(self, audio_path: Path) -> tuple[str, float, str]:
        """Transcribe audio file using Faster-Whisper.

        Returns:
            Tuple of (transcript_text, duration_seconds, language).
        """
        model = self._get_whisper_model()
        segments, info = model.transcribe(str(audio_path), beam_size=5)

        language = info.language
        duration_seconds = info.duration

        text_parts: list[str] = []
        for segment in segments:
            text_parts.append(segment.text)

        transcript_text = " ".join(text_parts).strip()
        logger.info(
            "Transcribed '{}': {:.1f}s, language={}, {} chars",
            audio_path.name,
            duration_seconds,
            language,
            len(transcript_text),
        )
        return transcript_text, duration_seconds, language

    async def _insert_chunks_to_qdrant(
        self,
        *,
        file_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        """Insert chunk embeddings into Qdrant with metadata."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct

            client = QdrantClient(url=self._settings.QDRANT_URL)
            collection = self._settings.QDRANT_COLLECTION

            try:
                existing = [c.name for c in client.get_collections().collections]
                if collection not in existing:
                    from qdrant_client.models import Distance, SparseIndexParams, SparseVectorParams, VectorParams
                    client.create_collection(
                        collection_name=collection,
                        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                        sparse_vectors_config={"bm25": SparseVectorParams(index=SparseIndexParams(on_disk=False))},
                    )
                    logger.info("Created Qdrant collection '{}' as fallback", collection)
            except Exception as exc:
                logger.warning("Fallback collection check failed: {}", exc)

            points = []
            now = datetime.now(timezone.utc).isoformat()
            for idx, (chunk_text_val, vector) in enumerate(zip(chunks, embeddings)):
                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "file_id": file_id,
                            "file_type": "audio",
                            "chunk_index": idx,
                            "chunk_text": chunk_text_val,
                            "created_at": now,
                        },
                    )
                )

            client.upsert(collection_name=collection, points=points)
            logger.info(
                "Inserted {} audio chunks into Qdrant for file {}",
                len(points),
                file_id,
            )
        except Exception as exc:
            logger.error("Qdrant insertion failed for file {}: {}", file_id, exc)
            raise


audio_ingestor = AudioIngestor()
