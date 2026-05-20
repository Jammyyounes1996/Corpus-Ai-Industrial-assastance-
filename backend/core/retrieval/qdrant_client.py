from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from backend.config.settings import get_settings
from backend.core.models.ollama_client import ollama_client


class QdrantRetriever:
    """Async-friendly Qdrant client with hybrid search (dense + sparse BM25)."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-initialize the Qdrant client."""
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(url=self._settings.QDRANT_URL)
            logger.info("Connected to Qdrant at {}", self._settings.QDRANT_URL)
        return self._client

    def ensure_collection(self) -> None:
        """Create the collection if it doesn't exist, with dense + sparse vectors."""
        from qdrant_client.models import (
            Distance,
            PointStruct,
            SparseIndexParams,
            SparseVectorParams,
            VectorParams,
        )

        client = self._get_client()
        collection = self._settings.QDRANT_COLLECTION

        existing = [c.name for c in client.get_collections().collections]
        if collection in existing:
            logger.info("Collection '{}' already exists", collection)
            return

        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE,
            ),
            sparse_vectors_config={
                "bm25": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False),
                ),
            },
        )
        logger.info("Created Qdrant collection '{}' with dense + sparse vectors", collection)

    async def generate_dense_vector(self, text: str) -> list[float]:
        """Generate a dense embedding vector using nomic-embed-text (768 dims).

        Args:
            text: Input text to embed.

        Returns:
            768-dimensional float vector.
        """
        return await ollama_client.embed_text(text)

    def tokenize_for_bm25(self, text: str) -> dict[int, float]:
        """Simple BM25-style sparse tokenization.

        Produces a sparse vector as {token_hash: tf} for Qdrant sparse indexing.

        Args:
            text: Input text to tokenize.

        Returns:
            Dict mapping token hashes to term frequencies.
        """
        words = text.lower().split()
        tf_map: dict[int, float] = {}
        for word in words:
            token_hash = hash(word) & 0xFFFFFFFF
            tf_map[token_hash] = tf_map.get(token_hash, 0) + 1.0
        return tf_map

    async def hybrid_query(
        self,
        query_text: str,
        *,
        limit: int = 10,
        file_type_filter: str | None = None,
        rrf_k: int = 60,
    ) -> list[dict]:
        """Execute a hybrid query combining dense and sparse (BM25) search.

        Uses Qdrant's query_points API for prefetch + RRF fusion.

        Args:
            query_text: The search query.
            limit: Maximum results to return.
            file_type_filter: Optional file type to filter by.
            rrf_k: RRF constant for score fusion.

        Returns:
            List of result dicts with id, score, payload.
        """
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchValue,
            Prefetch,
            Query,
            SparseVector,
        )

        client = self._get_client()
        collection = self._settings.QDRANT_COLLECTION

        dense_vector = await self.generate_dense_vector(query_text)
        sparse_vector = self.tokenize_for_bm25(query_text)

        prefetch_filter = None
        if file_type_filter:
            prefetch_filter = Filter(
                must=[FieldCondition(key="file_type", match=MatchValue(value=file_type_filter))]
            )

        sparse_vec = SparseVector(
            indices=list(sparse_vector.keys()),
            values=list(sparse_vector.values()),
        )

        results = client.query_points(
            collection_name=collection,
            prefetch=[
                Prefetch(
                    query=dense_vector,
                    using="",
                    limit=limit * 3,
                    filter=prefetch_filter,
                ),
                Prefetch(
                    query=sparse_vec,
                    using="bm25",
                    limit=limit * 3,
                    filter=prefetch_filter,
                ),
            ],
            query=Query(fusion=rrf_k),
            limit=limit,
        )

        return [
            {
                "id": str(point.id),
                "score": point.score,
                "payload": point.payload or {},
            }
            for point in results.points
        ]


qdrant_retriever = QdrantRetriever()
