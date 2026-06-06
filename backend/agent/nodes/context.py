from __future__ import annotations

import time

from loguru import logger

from backend.agent.state import AgentState
from backend.agent.streaming import deduplicate_sources, emit_thinking_step
from backend.agent.utils.rrf_fusion import rrf_fusion
from backend.config.settings import get_settings
from backend.core.retrieval.reranker import reranker


settings = get_settings()

# Conservative relevance gate. Anything below this is treated as off-topic and
# excluded from `retrieved_context` / `sources` / GROUNDED_RAG.
# Score scale is the post-rerank / post-retrieval score (0..1).
MIN_RELEVANCE_SCORE = 0.45
# Minimum number of chunks that must pass the gate before we are willing to
# enter GROUNDED_RAG mode.
MIN_RELEVANT_CHUNKS_FOR_GROUNDED = 1


# Lines containing any of these markers in conversation history are stripped
# before being passed into a new prompt. They are the typical "leakage"
# fingerprints from a previous GROUNDED_RAG answer.
_LEAKAGE_MARKERS = (
    "Sources:",
    "Source:",
    "According to",
    "Based on",
    "based on the provided text",
    "based on the document",
    "based on the documents",
    "based on the attached",
    "retrieved context",
    "Retrieved Context",
    "النص المقدم",
    "النص الذي قدمته",
    "بناءً على النص",
    "بناء على النص",
    "بناءً على الملف",
    "بناء على الملف",
    "بناء على الوثائق",
    "بناءً على الوثائق",
    "حسب الملف",
    "حسب التقرير",
    "حسب المستند",
    "المصادر",
    "النصوص المقدمة",
)


def _sanitize_history_lines(content: str) -> str:
    """Remove leakage-marker lines from a single message body.

    Lines whose stripped form starts with or contains any marker are dropped.
    Returns the cleaned multi-line string (may be empty).
    """
    if not content:
        return ""
    cleaned: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned.append(line)
            continue
        if any(marker in stripped for marker in _LEAKAGE_MARKERS):
            continue
        cleaned.append(line)
    out = "\n".join(cleaned).strip()
    return out


def _build_history_text(
    history: list[dict],
    prompt_mode: str,
    current_message_id: str | None,
) -> str:
    """Build the history block for a prompt, sanitized per prompt_mode.

    - GENERAL / GENERAL_CHAT: return "" (no history at all — prevents any
      previous grounded answer from leaking into a new general question).
    - INDUSTRIAL_GENERAL: keep at most the last 2 user/assistant turns,
      with leakage markers stripped.
    - GROUNDED_RAG: keep the last few sanitized turns for follow-up
      continuity, with leakage markers stripped.
    - CONSERVATIVE_NO_SOURCE: no history.
    """
    if not history:
        return ""
    if prompt_mode in ("GENERAL", "CONSERVATIVE_NO_SOURCE"):
        return ""

    if prompt_mode == "INDUSTRIAL_GENERAL":
        max_turns = 4  # ~2 user + 2 assistant
    else:
        max_turns = 6

    recent = history[-max_turns:]
    lines: list[str] = []
    for message in recent:
        if message.get("id") and message.get("id") == current_message_id:
            continue
        role = str(message.get("role", "user")).strip().capitalize() or "User"
        raw_content = str(message.get("content", "")).strip()
        if not raw_content:
            continue

        if role.lower() == "system" and raw_content.startswith("[Summary]"):
            # Summaries are model-generated; still sanitize for safety.
            cleaned = _sanitize_history_lines(raw_content)
            if cleaned:
                lines.append(cleaned)
            continue

        cleaned = _sanitize_history_lines(raw_content)
        if not cleaned:
            continue
        lines.append(f"{role}: {cleaned}")
    return "\n".join(lines)


def _get_effective_score(item: dict) -> float:
    return float(item.get("rerank_score", item.get("retrieval_score", item.get("score", 0.0))))


def _build_sources(items: list[dict]) -> list[dict]:
    return [
        {
            "source": item.get("source", ""),
            "type": item.get("type", ""),
            "score": _get_effective_score(item),
            "file_id": item.get("file_id", ""),
            "file_name": item.get("file_name", "")
            or _extract_filename(item.get("source", "")),
            "file_type": item.get("file_type", "unknown"),
            "chunk_index": item.get("chunk_index", 0),
            "excerpt": (item.get("content", "") or "")[:200],
        }
        for item in items
    ]


def _emit_rag_trace(
    state: AgentState,
    query_category: str,
    prompt_mode: str,
    relevant_count: int,
    sources: list[dict],
    context_length: int,
    filtered_count: int | None = None,
) -> None:
    logger.info(
        "RAG_TRACE chat_id={} message_id={} query={!r} category={} routes={} "
        "qdrant_called={} groundx_called={} ocr_called={} attached_files={} "
        "selected_scope={} context_length={} relevant_chunks={} source_files={} "
        "prompt_mode={} history_chars={} retrieval_skipped_reason={!r} "
        "answer_mode={} retrieval_provider={} mode_decision={} "
        "groundx_global_search_allowed={} qdrant_global_audio_search_allowed={} "
        "no_match_message_type={!r}",
        state.get("chat_id", ""),
        state.get("message_id", ""),
        (state.get("query", "") or "")[:120],
        query_category,
        state.get("routes", []),
        bool(state.get("qdrant_called")),
        bool(state.get("groundx_called")),
        bool(state.get("ocr_called")),
        list(state.get("attached_files") or []),
        list(state.get("selected_scope") or []),
        context_length,
        relevant_count,
        [s.get("file_name") or s.get("source") for s in sources],
        prompt_mode,
        len(state.get("history_text", "")),
        state.get("retrieval_skipped_reason", ""),
        state.get("answer_mode", ""),
        state.get("retrieval_provider", ""),
        state.get("mode_decision", ""),
        state.get("groundx_global_search_allowed", False),
        state.get("qdrant_global_audio_search_allowed", False),
        state.get("no_match_message_type", ""),
    )
    if filtered_count is not None and filtered_count > 0:
        logger.info(
            "Filtered {} chunks below relevance threshold {} (category={})",
            filtered_count, MIN_RELEVANCE_SCORE, query_category,
        )


def _build_context_return(state: AgentState) -> dict:
    return {
        "context": state.get("context", ""),
        "retrieved_context": state.get("retrieved_context", ""),
        "history_text": state.get("history_text", ""),
        "prompt_mode": state.get("prompt_mode", ""),
        "sources": state.get("sources", []),
        "thinking_steps": state.get("thinking_steps", []),
        "no_match_message_type": state.get("no_match_message_type", ""),
    }


def _extract_filename(source: str) -> str:
    if "#" in source:
        return source.split("#")[0]
    return source


async def context_synthesis_node(state: AgentState) -> AgentState:
    start_time = time.perf_counter()
    logger.info(f"Executing context_synthesis_node for query: {state.get('query', '')[:50]}")
    state.setdefault("thinking_steps", []).append(
        emit_thinking_step(
            "context_synthesis_node",
            "Combining retrieved context...",
            {"node": "context_synthesis_node", "status": "in_progress"},
        )
    )
    try:
        query_category = state.get("query_category", "UNKNOWN")

        pdf_results = state.get("groundx_results", []) or []
        vector_results = state.get("qdrant_results", []) or []
        ocr_results = state.get("ocr_results", []) or []

        normalized_pdf = [
            {
                "item_id": item.get("item_id") or item.get("id") or item.get("source") or f"groundx-{idx}",
                "content": item.get("content") or item.get("text") or "",
                "score": item.get("score", 0.0),
                "source": item.get("source") or item.get("file") or "groundx",
                "file_id": item.get("file_id", ""),
                "file_name": item.get("file_name", ""),
                "file_type": item.get("file_type", "pdf"),
                "chunk_index": item.get("chunk_index", 0),
                "type": "groundx",
            }
            for idx, item in enumerate(pdf_results)
        ]

        normalized_vector = [
            {
                "item_id": item.get("item_id") or item.get("id") or item.get("source") or f"qdrant-{idx}",
                "content": item.get("content") or item.get("text") or "",
                "score": item.get("score", 0.0),
                "retrieval_score": item.get("retrieval_score", item.get("score", 0.0)),
                "source": item.get("source") or item.get("file") or "qdrant",
                "file_id": item.get("file_id", ""),
                "file_name": item.get("file_name", ""),
                "file_type": item.get("file_type", "unknown"),
                "chunk_index": item.get("chunk_index", 0),
                "type": "qdrant",
            }
            for idx, item in enumerate(vector_results)
        ]

        normalized_ocr = [
            {
                "item_id": item.get("item_id") or item.get("chunk_id") or f"ocr-{idx}",
                "content": item.get("content") or "",
                "score": item.get("score", 1.0),
                "source": item.get("file_name") or item.get("file_id") or "ocr",
                "file_id": item.get("file_id", ""),
                "file_name": item.get("file_name", ""),
                "file_type": "image",
                "chunk_index": 0,
                "type": "ocr",
            }
            for idx, item in enumerate(ocr_results)
        ]

        # ── answer_mode fast-path (before fusion/rerank) ──
        answer_mode = state.get("answer_mode")
        if answer_mode is not None:
            if answer_mode == "general":
                state["prompt_mode"] = "GENERAL"
                state["retrieved_context"] = ""
                state["context"] = ""
                state["sources"] = []
                state["no_match_message_type"] = ""
                history_text = _build_history_text(
                    state.get("history", []) or [],
                    "GENERAL",
                    state.get("message_id"),
                )
                state["history_text"] = history_text
                _emit_rag_trace(state, query_category, "GENERAL", 0, [], 0, filtered_count=None)
                return _build_context_return(state)
            elif answer_mode == "groundx":
                groundx_items = [
                    item for item in normalized_pdf if _get_effective_score(item) >= 0.60
                ]
                if len(groundx_items) >= MIN_RELEVANT_CHUNKS_FOR_GROUNDED:
                    prompt_mode = "GROUNDED_RAG"
                    gx_context = "\n\n".join(
                        item.get("content", "") for item in groundx_items if item.get("content")
                    )
                    sources = _build_sources(groundx_items)
                    state["prompt_mode"] = prompt_mode
                    state["retrieved_context"] = gx_context
                    state["context"] = gx_context
                    state["sources"] = sources
                    state["no_match_message_type"] = ""
                else:
                    state["prompt_mode"] = "CONSERVATIVE_NO_SOURCE"
                    state["retrieved_context"] = ""
                    state["context"] = ""
                    state["sources"] = []
                    state["no_match_message_type"] = "groundx_no_match"
                history_text = _build_history_text(
                    state.get("history", []) or [],
                    state["prompt_mode"],
                    state.get("message_id"),
                )
                state["history_text"] = history_text
                _emit_rag_trace(state, query_category, state["prompt_mode"],
                                len(groundx_items), state["sources"], len(state.get("retrieved_context", "")),
                                filtered_count=len(normalized_pdf) - len(groundx_items))
                return _build_context_return(state)
            elif answer_mode == "audio":
                audio_items = [
                    item for item in normalized_vector
                    if item.get("file_type") == "audio"
                    and _get_effective_score(item) >= 0.48
                ]
                if len(audio_items) >= MIN_RELEVANT_CHUNKS_FOR_GROUNDED:
                    prompt_mode = "GROUNDED_RAG"
                    audio_context = "\n\n".join(
                        item.get("content", "") for item in audio_items if item.get("content")
                    )
                    sources = _build_sources(audio_items)
                    state["prompt_mode"] = prompt_mode
                    state["retrieved_context"] = audio_context
                    state["context"] = audio_context
                    state["sources"] = sources
                    state["no_match_message_type"] = ""
                else:
                    state["prompt_mode"] = "CONSERVATIVE_NO_SOURCE"
                    state["retrieved_context"] = ""
                    state["context"] = ""
                    state["sources"] = []
                    state["no_match_message_type"] = "audio_no_match"
                history_text = _build_history_text(
                    state.get("history", []) or [],
                    state["prompt_mode"],
                    state.get("message_id"),
                )
                state["history_text"] = history_text
                _emit_rag_trace(state, query_category, state["prompt_mode"],
                                len(audio_items), state["sources"], len(state.get("retrieved_context", "")),
                                filtered_count=len(normalized_vector) - len(audio_items))
                return _build_context_return(state)

        fused_results = rrf_fusion([normalized_pdf, normalized_vector, normalized_ocr])
        if settings.RERANKER_ENABLED:
            top_fused = await reranker.rerank(
                state.get("query", ""),
                fused_results,
                settings.RERANKER_TOP_K,
            )
        else:
            top_fused = fused_results[: settings.RERANKER_TOP_K]
        # Apply relevance gate. For CURRENT_ATTACHMENT_QA we trust the user's
        # explicit attachment, but we still apply the gate to avoid mixing in
        # off-topic chunks from the same file.
        if query_category == "CURRENT_ATTACHMENT_QA":
            # Slightly lower bar — the user explicitly attached this content.
            threshold = max(0.25, MIN_RELEVANCE_SCORE - 0.20)
        else:
            threshold = MIN_RELEVANCE_SCORE
        relevant = [item for item in top_fused if _get_effective_score(item) >= threshold]
        filtered_count = len(top_fused) - len(relevant)

        # Build retrieved_context ONLY from chunks that passed the gate.
        fused_context = "\n\n".join(
            item.get("content", "") for item in relevant if item.get("content")
        )
        ocr_context = "\n\n".join(
            item.get("content", "") for item in normalized_ocr if item.get("content")
        )

        retrieved_parts: list[str] = []
        if fused_context:
            retrieved_parts.append(f"Retrieved Context:\n{fused_context}")
        if ocr_context and query_category == "CURRENT_ATTACHMENT_QA":
            retrieved_parts.append(f"Attached File OCR Context:\n{ocr_context}")
        retrieved_context = "\n\n".join(retrieved_parts)

        # Select prompt_mode based on category AND whether we actually have
        # enough relevant grounded content. Weak chunks can NEVER promote us
        # into GROUNDED_RAG.
        relevant_chunk_count = len(relevant) + (
            len([o for o in normalized_ocr if o.get("content")])
            if query_category == "CURRENT_ATTACHMENT_QA"
            else 0
        )
        has_real_retrieval = (
            bool(retrieved_context)
            and relevant_chunk_count >= MIN_RELEVANT_CHUNKS_FOR_GROUNDED
        )

        if query_category == "GENERAL_CHAT":
            prompt_mode = "GENERAL"
        elif query_category == "INDUSTRIAL_KNOWLEDGE" and not has_real_retrieval:
            prompt_mode = "INDUSTRIAL_GENERAL"
        elif has_real_retrieval and query_category in (
            "CURRENT_ATTACHMENT_QA",
            "FILE_QA",
            "RAG_REQUIRED",
        ):
            prompt_mode = "GROUNDED_RAG"
        elif query_category in ("FILE_QA", "RAG_REQUIRED", "CURRENT_ATTACHMENT_QA"):
            prompt_mode = "CONSERVATIVE_NO_SOURCE"
        elif query_category == "INDUSTRIAL_KNOWLEDGE":
            prompt_mode = "INDUSTRIAL_GENERAL"
        elif query_category == "UNKNOWN":
            prompt_mode = "CONSERVATIVE_NO_SOURCE"
        else:
            prompt_mode = "GENERAL"

        # Hard clear: only GROUNDED_RAG may carry retrieved_context / sources.
        if prompt_mode != "GROUNDED_RAG":
            retrieved_context = ""
            sources: list[dict] = []
        else:
            sources = [
                {
                    "source": item.get("source", ""),
                    "type": item.get("type", ""),
                    "score": _get_effective_score(item),
                    "file_id": item.get("file_id", ""),
                    "file_name": item.get("file_name", "")
                    or _extract_filename(item.get("source", "")),
                    "file_type": item.get("file_type", "unknown"),
                    "chunk_index": item.get("chunk_index", 0),
                    "excerpt": (item.get("content", "") or "")[:200],
                }
                for item in relevant
            ]
            if query_category == "CURRENT_ATTACHMENT_QA":
                for item in normalized_ocr:
                    if not item.get("content"):
                        continue
                    sources.append(
                        {
                            "source": item.get("source", ""),
                            "type": "ocr",
                            "score": item.get("score", 1.0),
                            "file_id": item.get("file_id", ""),
                            "file_name": item.get("file_name", ""),
                            "file_type": "image",
                            "chunk_index": 0,
                            "excerpt": (item.get("content", "") or "")[:200],
                        }
                    )
            sources = deduplicate_sources(sources)

        # Build sanitized history text per prompt_mode.
        history = state.get("history", []) or []
        history_text = _build_history_text(
            history,
            prompt_mode,
            state.get("message_id"),
        )

        state["retrieved_context"] = retrieved_context
        state["history_text"] = history_text
        state["context"] = retrieved_context
        state["prompt_mode"] = prompt_mode
        state["sources"] = sources
        state.setdefault("no_match_message_type", "")

        _emit_rag_trace(
            state, query_category, prompt_mode,
            len(relevant) if prompt_mode == "GROUNDED_RAG" else 0,
            sources, len(retrieved_context),
            filtered_count=filtered_count,
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        state.setdefault("thinking_steps", []).append(
            emit_thinking_step(
                "context_synthesis_node",
                "Context synthesis completed.",
                {
                    "node": "context_synthesis_node",
                    "status": "completed",
                    "duration_ms": duration_ms,
                    "relevant_count": len(relevant),
                    "filtered_count": filtered_count,
                    "threshold": threshold,
                    "prompt_mode": prompt_mode,
                },
            )
        )
        return _build_context_return(state)
    except Exception as exc:
        logger.error(f"context_synthesis_node failed: {exc}")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        state.setdefault("thinking_steps", []).append(
            emit_thinking_step(
                "context_synthesis_node",
                f"Context synthesis failed: {exc}",
                {"node": "context_synthesis_node", "status": "failed", "duration_ms": duration_ms},
            )
        )
        raise
