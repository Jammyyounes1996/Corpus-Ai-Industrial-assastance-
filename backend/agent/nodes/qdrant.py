from __future__ import annotations

import time
from collections import defaultdict

from loguru import logger

from backend.agent.state import AgentState
from backend.core.retrieval.qdrant_client import qdrant_retriever


DEFAULT_QDRANT_TOP_K = 15
MAX_CHUNKS_PER_FILE = 3
# Hard relevance floor applied at the retrieval layer. Chunks below this score
# are dropped before they ever enter the fusion / context pipeline.
QDRANT_HARD_RELEVANCE_FLOOR = 0.30

# Categories that genuinely need document retrieval.
_RETRIEVAL_CATEGORIES = {"CURRENT_ATTACHMENT_QA", "FILE_QA", "RAG_REQUIRED"}


async def qdrant_retrieve_node(state: AgentState) -> AgentState:
    """Retrieve vector-grounded context from Qdrant with strict scoping.

    Architecture rule: Qdrant NEVER runs as a global search. It requires an
    explicit scope — current-request attached_files OR a selected scope
    (selected_files / project / KB IDs in state['selected_scope']).

    If no explicit scope is present, Qdrant is skipped and returns zero
    chunks. This prevents contamination of unrelated answers with old
    indexed content.
    """
    start = time.perf_counter()
    answer_mode = state.get("answer_mode")

    if answer_mode is not None:
        if answer_mode != "audio":
            logger.info(
                "qdrant_retrieve: skipped (answer_mode={}, not audio)", answer_mode
            )
            return {"qdrant_results": [], "qdrant_called": False}

        try:
            logger.info("QDRANT_GLOBAL_AUDIO_SEARCH_ALLOWED answer_mode=audio")
            raw_results = await qdrant_retriever.hybrid_query(
                query_text=state["query"],
                limit=DEFAULT_QDRANT_TOP_K,
                file_id_filter=None,
            )

            file_counts: defaultdict[str, int] = defaultdict(int)
            results: list[dict] = []

            for idx, result in enumerate(raw_results):
                payload = result.get("payload", {}) or {}
                chunk_text = payload.get("chunk_text", "")
                file_id = str(payload.get("file_id", ""))
                chunk_index = int(payload.get("chunk_index", 0) or 0)
                score = float(result.get("score") or 0.0)
                result_id = str(result.get("id") or f"qdrant-{idx}")
                file_type = payload.get("file_type", "unknown")

                if score < QDRANT_HARD_RELEVANCE_FLOOR:
                    continue

                if file_type != "audio":
                    continue

                if file_id and file_counts[file_id] >= MAX_CHUNKS_PER_FILE:
                    continue

                file_counts[file_id] += 1
                original_name = payload.get("original_name", "")
                if not original_name:
                    original_name = f"Audio file {file_id} chunk {chunk_index}"

                results.append(
                    {
                        "id": result_id,
                        "item_id": result_id,
                        "content": chunk_text,
                        "text": chunk_text,
                        "source": f"{file_id}#chunk-{chunk_index}"
                        if file_id
                        else result_id,
                        "file_id": file_id,
                        "file_name": original_name,
                        "file_type": file_type,
                        "chunk_index": chunk_index,
                        "score": score,
                        "retrieval_score": score,
                        "payload": payload,
                    }
                )

            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "Qdrant audio retrieval returned {} results (from {} raw) in {}ms",
                len(results),
                len(raw_results),
                duration_ms,
            )
            return {
                "qdrant_results": results,
                "qdrant_called": True,
                "qdrant_global_audio_search_allowed": True,
            }
        except Exception as exc:
            logger.exception("Qdrant audio retrieval failed: %s", exc)
            return {"qdrant_results": [], "qdrant_called": True}

    routes = state.get("routes", []) or []
    if "qdrant" not in routes:
        logger.info("qdrant_retrieve: skipped (not routed, routes={})", routes)
        return {"qdrant_results": [], "qdrant_called": False}

    category = state.get("query_category", "UNKNOWN")

    # Reject categories that must never trigger document retrieval, even if
    # something upstream incorrectly added "qdrant" to routes.
    if category not in _RETRIEVAL_CATEGORIES:
        logger.info(
            "qdrant_retrieve: skipped (category={} is not a retrieval category)",
            category,
        )
        return {
            "qdrant_results": [],
            "qdrant_called": False,
            "retrieval_skipped_reason": f"qdrant_skipped_category_{category}",
        }

    attached_files = state.get("attached_files") or []
    selected_scope = state.get("selected_scope") or []

    file_id_filter: list[str] | None = None
    if attached_files:
        file_id_filter = list(attached_files)
    elif selected_scope:
        file_id_filter = list(selected_scope)

    if not file_id_filter:
        # No explicit scope -> never search the whole vector store.
        logger.info(
            "qdrant_retrieve: skipped (no explicit scope; category={})",
            category,
        )
        return {
            "qdrant_results": [],
            "qdrant_called": False,
            "retrieval_skipped_reason": "qdrant_skipped_no_scope",
        }

    try:
        raw_results = await qdrant_retriever.hybrid_query(
            query_text=state["query"],
            limit=DEFAULT_QDRANT_TOP_K,
            file_id_filter=file_id_filter,
        )

        file_counts: defaultdict[str, int] = defaultdict(int)
        results: list[dict] = []

        for idx, result in enumerate(raw_results):
            payload = result.get("payload", {}) or {}
            chunk_text = payload.get("chunk_text", "")
            file_id = str(payload.get("file_id", ""))
            chunk_index = int(payload.get("chunk_index", 0) or 0)
            score = float(result.get("score") or 0.0)
            result_id = str(result.get("id") or f"qdrant-{idx}")

            # Hard relevance floor before any downstream processing.
            if score < QDRANT_HARD_RELEVANCE_FLOOR:
                continue

            # Defense in depth: only accept chunks whose file_id is in the
            # requested scope.
            if file_id and file_id not in file_id_filter:
                continue

            if file_id and file_counts[file_id] >= MAX_CHUNKS_PER_FILE:
                continue

            file_counts[file_id] += 1
            results.append(
                {
                    "id": result_id,
                    "item_id": result_id,
                    "content": chunk_text,
                    "text": chunk_text,
                    "source": f"{file_id}#chunk-{chunk_index}" if file_id else result_id,
                    "file_id": file_id,
                    "file_name": payload.get("original_name", ""),
                    "file_type": payload.get("file_type", "unknown"),
                    "chunk_index": chunk_index,
                    "score": score,
                    "retrieval_score": score,
                    "payload": payload,
                }
            )

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "Qdrant retrieval returned {} results (from {} raw) in {}ms (scope=file_ids:{})",
            len(results),
            len(raw_results),
            duration_ms,
            len(file_id_filter),
        )
        return {"qdrant_results": results, "qdrant_called": True}
    except Exception as exc:
        logger.exception("Qdrant retrieval failed: %s", exc)
        return {"qdrant_results": [], "qdrant_called": True}
