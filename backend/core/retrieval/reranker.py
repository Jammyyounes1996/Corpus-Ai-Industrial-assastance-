from __future__ import annotations

import asyncio
from typing import Any

from backend.config.settings import get_settings

try:
    from sentence_transformers import CrossEncoder

    RERANKER_AVAILABLE = True
except ImportError:
    CrossEncoder = None
    RERANKER_AVAILABLE = False


class Reranker:
    """Cross-encoder reranker for retrieval chunks."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._model: Any = None

    def _get_model(self) -> Any:
        if not RERANKER_AVAILABLE:
            return None
        if self._model is None:
            self._model = CrossEncoder(self._settings.RERANKER_MODEL)
        return self._model

    async def rerank(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        if not chunks or top_k <= 0:
            return []

        if not RERANKER_AVAILABLE:
            return chunks[:top_k]

        model = self._get_model()
        if model is None:
            return chunks[:top_k]
        pairs = [(query, chunk.get("content", "")) for chunk in chunks]
        scores = await asyncio.get_event_loop().run_in_executor(
            None, model.predict, pairs
        )

        rescored: list[dict[str, Any]] = []
        for chunk, score in zip(chunks, scores):
            item = dict(chunk)
            item["rerank_score"] = float(score)
            rescored.append(item)

        rescored.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
        return rescored[:top_k]


reranker = Reranker()
