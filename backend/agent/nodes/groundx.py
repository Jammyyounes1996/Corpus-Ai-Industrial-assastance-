from __future__ import annotations

import time

from loguru import logger

from backend.agent.state import AgentState
from backend.core.retrieval.groundx_client import groundx_client


# GroundX is a global PDF index — it cannot be safely scoped per-request the
# same way Qdrant can. To avoid leaking unrelated PDFs into general or
# industrial-concept answers, we only call GroundX when there is an explicit
# document-targeted query AND an explicit scope (attached_files or
# selected_scope).
_RETRIEVAL_CATEGORIES = {"CURRENT_ATTACHMENT_QA", "FILE_QA", "RAG_REQUIRED"}


async def groundx_retrieve_node(state: AgentState) -> AgentState:
    """Retrieve PDF-grounded context from GroundX with strict scoping.

    Never runs for general chat or industrial-concept questions. Never runs
    without an explicit scope.
    """
    start = time.perf_counter()
    answer_mode = state.get("answer_mode")

    if answer_mode is not None:
        if answer_mode != "groundx":
            logger.info(
                "groundx_retrieve: skipped (answer_mode={}, not groundx)",
                answer_mode,
            )
            return {"groundx_results": [], "groundx_called": False}

        try:
            logger.info("GROUNDX_GLOBAL_SEARCH_ALLOWED answer_mode=groundx")
            results = await groundx_client.search(state["query"])
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info(f"GroundX retrieval took {duration_ms:.2f}ms")
            return {
                "groundx_results": results,
                "groundx_called": True,
                "groundx_global_search_allowed": True,
            }
        except Exception as exc:
            logger.exception("GroundX retrieval failed: %s", exc)
            return {"groundx_results": [], "groundx_called": True}

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
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(f"GroundX retrieval took {duration_ms:.2f}ms")
        return {"groundx_results": results, "groundx_called": True}
    except Exception as exc:
        logger.exception("GroundX retrieval failed: %s", exc)
        return {"groundx_results": [], "groundx_called": True}
