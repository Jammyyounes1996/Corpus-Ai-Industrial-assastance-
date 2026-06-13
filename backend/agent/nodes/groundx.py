from __future__ import annotations

import time

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.state import AgentState
from backend.config.settings import get_settings
from backend.core.retrieval.groundx_client import groundx_client
from backend.database import crud


# GroundX is a global PDF index — it cannot be safely scoped per-request the
# same way Qdrant can. To avoid leaking unrelated PDFs into general or
# industrial-concept answers, we only call GroundX when there is an explicit
# document-targeted query AND an explicit scope (attached_files or
# selected_scope).
_RETRIEVAL_CATEGORIES = {"CURRENT_ATTACHMENT_QA", "FILE_QA", "RAG_REQUIRED"}
settings = get_settings()


async def groundx_retrieve_node(
    state: AgentState,
    session: AsyncSession | None = None,
) -> AgentState:
    """Retrieve PDF-grounded context from GroundX with strict scoping.

    Never runs for general chat or industrial-concept questions. Never runs
    without an explicit scope.
    """
    start = time.perf_counter()
    answer_mode = state.get("answer_mode")

    if not settings.GROUNDX_API_KEY or not settings.GROUNDX_BUCKET_ID:
        return {
            "groundx_results": [],
            "groundx_search_text": "",
            "groundx_called": False,
            "no_match_message_type": "groundx_not_ready",
        }

    ready_count = 0
    processing_count = 0
    if session is not None:
        ready_count = await crud.count_groundx_files_by_status(
            session,
            bucket_id=str(settings.GROUNDX_BUCKET_ID),
            statuses=["indexed"],
        )
        processing_count = await crud.count_groundx_files_by_status(
            session,
            bucket_id=str(settings.GROUNDX_BUCKET_ID),
            statuses=["queued", "processing"],
        )

    if answer_mode is not None:
        if answer_mode != "groundx":
            logger.info(
                "groundx_retrieve: skipped (answer_mode={}, not groundx)",
                answer_mode,
            )
            return {"groundx_results": [], "groundx_called": False}

        try:
            if session is not None and ready_count == 0:
                logger.info(
                    "GroundX retrieval skipped: no indexed files in bucket {} (processing={})",
                    settings.GROUNDX_BUCKET_ID,
                    processing_count,
                )
                return {
                    "groundx_results": [],
                    "groundx_search_text": "",
                    "groundx_called": False,
                    "groundx_global_search_allowed": True,
                    "no_match_message_type": "groundx_not_ready",
                }

            logger.info("GROUNDX_GLOBAL_SEARCH_ALLOWED answer_mode=groundx")
            logger.info(
                "GroundX search: answer_mode=groundx bucket_id={} query_len={}",
                settings.GROUNDX_BUCKET_ID,
                len(state.get("query", "")),
            )
            results = await groundx_client.search(state["query"])
            if isinstance(results, list):
                results = {"text": "", "results": results}
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "GroundX results count: {} ({}ms)",
                len(results.get("results", [])),
                duration_ms,
            )
            return {
                "groundx_results": results.get("results", []),
                "groundx_search_text": results.get("text", ""),
                "groundx_called": True,
                "groundx_global_search_allowed": True,
            }
        except Exception as exc:
            logger.exception("GroundX retrieval failed: %s", exc)
            return {"groundx_results": [], "groundx_search_text": "", "groundx_called": True}

    routes = state.get("routes", []) or []
    if "groundx" not in routes:
        logger.info("groundx_retrieve: skipped (not routed, routes={})", routes)
        return {"groundx_results": [], "groundx_called": False}

    category = state.get("query_category", "UNKNOWN")
    if category not in _RETRIEVAL_CATEGORIES:
        logger.info(
            "groundx_retrieve: skipped (category={} is not a retrieval category)",
            category,
        )
        return {
            "groundx_results": [],
            "groundx_called": False,
            "retrieval_skipped_reason": f"groundx_skipped_category_{category}",
        }

    attached_files = state.get("attached_files") or []
    selected_scope = state.get("selected_scope") or []
    if not attached_files and not selected_scope:
        # GroundX cannot be scoped to a specific document set per-request.
        # Without explicit scope we refuse to run it to avoid contaminating
        # answers with unrelated stored PDFs.
        logger.info(
            "groundx_retrieve: skipped (no explicit scope; category={})",
            category,
        )
        return {
            "groundx_results": [],
            "groundx_called": False,
            "retrieval_skipped_reason": "groundx_skipped_no_scope",
        }

    try:
        results = await groundx_client.search(state["query"])
        if isinstance(results, list):
            results = {"text": "", "results": results}
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(f"GroundX retrieval took {duration_ms:.2f}ms")
        return {
            "groundx_results": results.get("results", []),
            "groundx_search_text": results.get("text", ""),
            "groundx_called": True,
        }
    except Exception as exc:
        logger.exception("GroundX retrieval failed: %s", exc)
        return {"groundx_results": [], "groundx_search_text": "", "groundx_called": True}
