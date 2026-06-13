from __future__ import annotations

import asyncio

from loguru import logger

from backend.agent.state import AgentState
from backend.agent.streaming import emit_thinking_step
from backend.core.web_search.provider import WebSearchProvider


def _normalize_source(result: dict, index: int) -> dict:
    title = str(result.get("title") or result.get("url") or f"Web source {index + 1}")
    url = str(result.get("url") or "")
    snippet = str(result.get("snippet") or "Retrieved web result")
    source = str(result.get("source") or "web")
    published_date = result.get("published_date")
    return {
        "file_id": url,
        "file_name": title,
        "filename": title,
        "file_type": "text",
        "chunk_index": index,
        "score": 1.0,
        "excerpt": snippet,
        "type": "web",
        "url": url,
        "source": source,
        "published_date": published_date,
    }


async def _emit_workflow(
    token_queue: asyncio.Queue | None,
    label: str,
    *,
    status: str,
    metadata: dict | None = None,
) -> None:
    if token_queue is None:
        return
    payload = emit_thinking_step("WEB_SEARCH", label, {"status": status, **(metadata or {})})
    if metadata:
        payload["data"].update(metadata)
    await token_queue.put({"type": "workflow", "data": payload})


async def web_search_node(
    state: AgentState,
    token_queue: asyncio.Queue | None = None,
) -> AgentState:
    if not state.get("search_required"):
        await _emit_workflow(
            token_queue,
            "WEB_SEARCH skipped",
            status="skipped",
            metadata={"reason": state.get("search_reason") or "not_required"},
        )
        state["search_used"] = False
        state["web_results"] = []
        state["web_sources"] = []
        return state

    provider = WebSearchProvider()
    if not provider.is_configured():
        await _emit_workflow(
            token_queue,
            "WEB_SEARCH skipped",
            status="skipped",
            metadata={"reason": "not_configured"},
        )
        state["search_used"] = False
        state["search_error"] = "Web search is required for this request, but no provider/API key is configured."
        state["web_results"] = []
        state["web_sources"] = []
        return state

    await _emit_workflow(
        token_queue,
        "WEB_SEARCH started",
        status="in_progress",
        metadata={"provider": state.get("web_search_provider") or getattr(provider, "provider_name", "configured")},
    )
    try:
        results = await provider.search(state.get("query", ""))
    except Exception as exc:
        logger.warning("web_search_node failed: {}", exc)
        await _emit_workflow(
            token_queue,
            "WEB_SEARCH skipped",
            status="failed",
            metadata={"reason": str(exc)},
        )
        state["search_used"] = False
        state["search_error"] = f"Web search failed: {exc}"
        state["web_results"] = []
        state["web_sources"] = []
        return state

    web_sources = [_normalize_source(result, index) for index, result in enumerate(results)]
    state["search_used"] = bool(results)
    state["search_error"] = None
    state["web_results"] = results
    state["web_sources"] = web_sources
    state["sources"] = [*(state.get("sources") or []), *web_sources]
    await _emit_workflow(
        token_queue,
        "WEB_SEARCH completed",
        status="completed",
        metadata={"result_count": len(results)},
    )
    return state
