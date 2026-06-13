"""LangGraph graph compilation for RAG agent with conditional routing."""

from __future__ import annotations

import asyncio
import time
from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.agent.nodes.groundx import groundx_retrieve_node
from backend.agent.nodes.answer import answer_node as answer_node_impl
from backend.agent.nodes.ocr import ocr_node
from backend.agent.nodes.qdrant import qdrant_retrieve_node
from backend.agent.nodes.router import router_node
from backend.agent.nodes.web_search import web_search_node
from backend.agent.nodes.context import context_synthesis_node
from backend.agent.streaming import emit_thinking_step
from backend.agent.streaming import deduplicate_sources
from backend.agent.state import AgentState
from backend.agent.utils.rrf_fusion import rrf_fusion
from backend.config.settings import get_settings
from backend.core.retrieval.reranker import reranker


settings = get_settings()


def _wrap_node_with_queue(fn, node_name: str, queue: asyncio.Queue):
    """Wrap a node function to emit thinking_step events to the queue."""
    is_coro = asyncio.iscoroutinefunction(fn)

    async def wrapped(state):
        start = time.perf_counter()
        await queue.put({
                "type": "workflow",
            "data": emit_thinking_step(
                node_name, f"{node_name} started",
                {"node": node_name, "status": "in_progress"},
            ),
        })
        result = (await fn(state)) if is_coro else fn(state)
        duration_ms = int((time.perf_counter() - start) * 1000)
        await queue.put({
                "type": "workflow",
            "data": emit_thinking_step(
                node_name, f"{node_name} completed",
                {"node": node_name, "status": "completed", "duration_ms": duration_ms},
            ),
        })
        return result

    return wrapped

def ocr_skip_node(state: AgentState) -> AgentState:
    return {"ocr_results": []}


def retrieval_skip_node(state: AgentState) -> AgentState:
    """Skip all retrieval — used for general chat queries."""
    return {
        "groundx_results": [],
        "qdrant_results": [],
        "ocr_results": [],
    }


def _retrieval_route(state: AgentState) -> str:
    """Determine retrieval path based on query classification."""
    routes = state.get("routes", [])
    if not routes:
        return "skip_retrieval"
    if "ocr" in routes and "qdrant" not in routes and "groundx" not in routes:
        return "ocr_only"
    return "do_retrieval"


def _ocr_route(state: AgentState) -> str:
    if state.get("attached_files"):
        return "with_ocr"
    return "without_ocr"


def compiled_agent_graph(
    session: AsyncSession,
    token_queue: asyncio.Queue | None = None,
) -> Any:
    """Compile and return the LangGraph agent graph."""
    graph = StateGraph(AgentState)

    ocr_node_with_session = partial(ocr_node, session=session)
    router_node_with_session = partial(router_node, session=session)
    groundx_node_with_session = partial(groundx_retrieve_node, session=session)
    answer_node_with_queue = partial(answer_node_impl, token_queue=token_queue)
    web_search_node_with_queue = partial(web_search_node, token_queue=token_queue)

    if token_queue is not None:
        graph.add_node("router", _wrap_node_with_queue(router_node_with_session, "router", token_queue))
        graph.add_node("groundx_retrieve", _wrap_node_with_queue(groundx_node_with_session, "groundx_retrieve", token_queue))
        graph.add_node("qdrant_retrieve", _wrap_node_with_queue(qdrant_retrieve_node, "qdrant_retrieve", token_queue))
        graph.add_node("ocr_retrieve", _wrap_node_with_queue(ocr_node_with_session, "ocr_retrieve", token_queue))
        graph.add_node("ocr_skip", _wrap_node_with_queue(ocr_skip_node, "ocr_skip", token_queue))
        graph.add_node("retrieval_skip", _wrap_node_with_queue(retrieval_skip_node, "retrieval_skip", token_queue))
        graph.add_node("context_synthesis", _wrap_node_with_queue(context_synthesis_node, "context_synthesis", token_queue))
        graph.add_node("web_search", web_search_node_with_queue)
        graph.add_node("answer_node", answer_node_with_queue)
    else:
        graph.add_node("router", router_node_with_session)
        graph.add_node("groundx_retrieve", groundx_node_with_session)
        graph.add_node("qdrant_retrieve", qdrant_retrieve_node)
        graph.add_node("ocr_retrieve", ocr_node_with_session)
        graph.add_node("ocr_skip", ocr_skip_node)
        graph.add_node("retrieval_skip", retrieval_skip_node)
        graph.add_node("context_synthesis", context_synthesis_node)
        graph.add_node("web_search", web_search_node_with_queue)
        graph.add_node("answer_node", answer_node_with_queue)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        _retrieval_route,
        {
            "skip_retrieval": "retrieval_skip",
            "ocr_only": "ocr_retrieve",
            "do_retrieval": "groundx_retrieve",
        },
    )

    graph.add_edge("retrieval_skip", "context_synthesis")

    graph.add_edge("groundx_retrieve", "qdrant_retrieve")

    graph.add_conditional_edges(
        "qdrant_retrieve",
        _ocr_route,
        {
            "with_ocr": "ocr_retrieve",
            "without_ocr": "ocr_skip",
        },
    )

    graph.add_edge("ocr_retrieve", "context_synthesis")
    graph.add_edge("ocr_skip", "context_synthesis")

    graph.add_edge("context_synthesis", "web_search")
    graph.add_edge("web_search", "answer_node")
    graph.add_edge("answer_node", END)

    return graph.compile()


def build_graph(
    session: AsyncSession,
    token_queue: asyncio.Queue | None = None,
) -> Any:
    return compiled_agent_graph(session, token_queue)
